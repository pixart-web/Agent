from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.integrations.email.credentials import FernetSecretStore
from app.integrations.email.errors import EmailAuthenticationError, EmailNotFoundError
from app.integrations.email.oauth import (
    INVALID_STATE_MESSAGE,
    OAUTH_PROVIDER,
    OAUTH_PURPOSE,
    GmailOAuthClient,
)
from app.integrations.email.policy import EmailPolicy
from app.integrations.email.providers.gmail import GmailProvider
from app.integrations.email.schemas import (
    EmailAccountOutput,
    EmailListInput,
    EmailMessageInput,
    EmailMessageOutput,
    EmailMessagesOutput,
    EmailThreadInput,
    EmailThreadOutput,
)
from app.integrations.email.service import EmailService
from app.models.integration_account import IntegrationAccount
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.user import User
from app.models.workflow_enums import ActorType, IntegrationAccountStatus, IntegrationAccountType
from app.repositories.integration_account_repository import IntegrationAccountRepository
from app.repositories.integration_oauth_state_repository import (
    IntegrationOAuthStateRepository,
)
from app.schemas.email import (
    EmailAccountsOutput,
    EmailConnectOutput,
    EmailDisconnectInput,
    EmailIntegrationStatus,
)
from app.services.audit_service import AuditService

router = APIRouter(tags=["email"])


def _account(value: IntegrationAccount) -> EmailAccountOutput:
    return EmailAccountOutput(
        id=value.id,
        provider=value.provider,
        account_type=value.account_type.value
        if hasattr(value.account_type, "value")
        else value.account_type,
        email_address=value.email_address,
        status=value.status.value if hasattr(value.status, "value") else value.status,
        scopes=value.scopes,
        last_sync_at=value.last_sync_at,
    )


def _require_enabled(settings: Settings) -> None:
    if not settings.email_integration_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Email integration is disabled")


@router.get("/integrations/email/status", response_model=EmailIntegrationStatus)
def email_status(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailIntegrationStatus:
    accounts = IntegrationAccountRepository(db).list_owned(user.id)
    return EmailIntegrationStatus(
        enabled=settings.email_integration_enabled,
        provider=settings.email_provider,
        send_enabled=settings.email_send_enabled,
        mark_read_enabled=settings.email_mark_read_enabled,
        connected_accounts=sum(
            account.status == IntegrationAccountStatus.CONNECTED for account in accounts
        ),
    )


@router.get("/integrations/email/accounts", response_model=EmailAccountsOutput)
def email_accounts(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailAccountsOutput:
    return EmailAccountsOutput(
        accounts=[_account(value) for value in IntegrationAccountRepository(db).list_owned(user.id)]
    )


@router.post("/integrations/email/connect", response_model=EmailConnectOutput)
def email_connect(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailConnectOutput:
    _require_enabled(settings)
    oauth = GmailOAuthClient(settings)
    now = utc_now()
    oauth_state = IntegrationOAuthState(
        user_id=user.id,
        provider=OAUTH_PROVIDER,
        purpose=OAUTH_PURPOSE,
        expires_at=now + timedelta(minutes=settings.email_oauth_state_expire_minutes),
    )
    IntegrationOAuthStateRepository(db).add(oauth_state)
    db.flush()
    state_token = oauth.issue_state(
        user.id, state_id=oauth_state.id, expires_at=oauth_state.expires_at
    )
    db.commit()
    return EmailConnectOutput(authorization_url=oauth.authorization_url(state_token))


@router.get("/integrations/email/callback", response_class=RedirectResponse)
def email_callback(
    code: Annotated[str, Query(min_length=1)],
    state_token: Annotated[str, Query(alias="state", min_length=1)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    _require_enabled(settings)
    oauth = GmailOAuthClient(settings)
    claims = oauth.decode_state(state_token)
    consumed = IntegrationOAuthStateRepository(db).consume(
        claims.state_id,
        claims.user_id,
        OAUTH_PROVIDER,
        OAUTH_PURPOSE,
        utc_now(),
    )
    if not consumed:
        db.rollback()
        raise EmailAuthenticationError(INVALID_STATE_MESSAGE)
    db.commit()
    user_id = claims.user_id
    tokens = oauth.exchange_code(code)
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not isinstance(refresh_token, str) or not isinstance(access_token, str):
        raise EmailAuthenticationError("Google did not return an offline refresh token")
    policy = EmailPolicy(
        settings.email_allowed_account_list,
        max_recipients=settings.email_max_recipients,
        max_attachment_bytes=settings.email_max_attachment_bytes,
    )
    provider = GmailProvider(
        access_token,
        settings.email_api_timeout_seconds,
        max_body_chars=settings.email_max_body_chars,
        policy=policy,
    )
    try:
        profile = provider.profile()
    finally:
        provider.close()
    address = policy.authorize_account(str(profile.get("emailAddress", "")))
    external_id = str(profile.get("emailAddress", address))
    repository = IntegrationAccountRepository(db)
    account = repository.get_by_external(user_id, "gmail", external_id)
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    encrypted = store.encrypt({"refresh_token": refresh_token})
    if account is None:
        account = repository.add(
            IntegrationAccount(
                user_id=user_id,
                provider="gmail",
                account_type=IntegrationAccountType.PERSONAL,
                external_account_id=external_id,
                email_address=address,
                status=IntegrationAccountStatus.CONNECTED,
                scopes=oauth.scopes,
                encrypted_credentials=encrypted,
            )
        )
    else:
        account.email_address = address
        account.status = IntegrationAccountStatus.CONNECTED
        account.scopes = oauth.scopes
        account.encrypted_credentials = encrypted
    db.flush()
    AuditService(db).record(
        actor_type=ActorType.USER,
        actor_id=user_id,
        event_type="email_account_connected",
        resource_type="integration_account",
        resource_id=account.id,
        metadata={"provider": "gmail"},
        correlation_id=uuid4(),
    )
    db.commit()
    db.refresh(account)
    return RedirectResponse(
        url=f"{settings.web_origin_list[0]}/dashboard/integrations/email?connected=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/integrations/email/disconnect", response_model=EmailAccountOutput)
def email_disconnect(
    value: EmailDisconnectInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailAccountOutput:
    _require_enabled(settings)
    account = IntegrationAccountRepository(db).get_owned(value.account_id, user.id)
    if account is None:
        raise EmailNotFoundError("Email account was not found")
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    credentials = store.decrypt(account.encrypted_credentials)
    refresh_token = credentials.get("refresh_token")
    if isinstance(refresh_token, str):
        GmailOAuthClient(settings).revoke(refresh_token)
    account.status = IntegrationAccountStatus.REVOKED
    account.encrypted_credentials = store.encrypt({"revoked": True})
    AuditService(db).record(
        actor_type=ActorType.USER,
        actor_id=user.id,
        event_type="email_account_disconnected",
        resource_type="integration_account",
        resource_id=account.id,
        metadata={"provider": account.provider},
        correlation_id=uuid4(),
    )
    db.commit()
    return _account(account)


def _context(user_id: UUID) -> ExecutionContext:
    identifier = uuid4()
    return ExecutionContext(
        user_id=user_id,
        command_id=identifier,
        task_id=identifier,
        action_id=identifier,
        execution_id=identifier,
        correlation_id=identifier,
        credentials=EnvironmentCredentialProvider(),
    )


def _email_service(db: Session, settings: Settings) -> EmailService:
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    return EmailService(settings=settings, session_factory=factory)


@router.get("/email/messages", response_model=EmailMessagesOutput)
def list_email_messages(
    account_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=25, ge=1, le=100),
    page_token: str | None = None,
) -> EmailMessagesOutput:
    return _email_service(db, settings).list_messages(
        _context(user.id), EmailListInput(account_id=account_id, limit=limit, page_token=page_token)
    )


@router.get("/email/messages/{message_id}", response_model=EmailMessageOutput)
def get_email_message(
    message_id: str,
    account_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailMessageOutput:
    return _email_service(db, settings).get_message(
        _context(user.id), EmailMessageInput(account_id=account_id, message_id=message_id)
    )


@router.get("/email/threads/{thread_id}", response_model=EmailThreadOutput)
def get_email_thread(
    thread_id: str,
    account_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailThreadOutput:
    return _email_service(db, settings).get_thread(
        _context(user.id), EmailThreadInput(account_id=account_id, thread_id=thread_id)
    )
