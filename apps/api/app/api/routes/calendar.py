from datetime import datetime, timedelta
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
from app.integrations.calendar.errors import (
    CalendarAuthenticationError,
    CalendarNotFoundError,
)
from app.integrations.calendar.oauth import (
    INVALID_STATE_MESSAGE,
    OAUTH_PROVIDER,
    OAUTH_PURPOSE,
    GoogleCalendarOAuthClient,
)
from app.integrations.calendar.policy import CalendarPolicy
from app.integrations.calendar.providers.google import GoogleCalendarProvider
from app.integrations.calendar.schemas import (
    CalendarAvailabilityInput,
    CalendarAvailabilityOutput,
    CalendarEventInput,
    CalendarEventOutput,
    CalendarEventsInput,
    CalendarEventsOutput,
    CalendarListInput,
    CalendarListOutput,
    CalendarSearchInput,
)
from app.integrations.calendar.service import CalendarService
from app.integrations.credentials import EnvironmentCredentialProvider
from app.integrations.email.credentials import FernetSecretStore
from app.models.integration_account import IntegrationAccount
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.user import User
from app.models.workflow_enums import (
    ActorType,
    IntegrationAccountStatus,
    IntegrationAccountType,
)
from app.repositories.integration_account_repository import IntegrationAccountRepository
from app.repositories.integration_oauth_state_repository import (
    IntegrationOAuthStateRepository,
)
from app.schemas.calendar import (
    CalendarAccountOutput,
    CalendarAccountsOutput,
    CalendarConnectOutput,
    CalendarDisconnectInput,
    CalendarIntegrationStatus,
)
from app.services.audit_service import AuditService

router = APIRouter(tags=["calendar"])


def _account(value: IntegrationAccount) -> CalendarAccountOutput:
    return CalendarAccountOutput(
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
    if not settings.calendar_integration_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Calendar integration is disabled")


@router.get("/integrations/calendar/status", response_model=CalendarIntegrationStatus)
def calendar_status(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarIntegrationStatus:
    accounts = IntegrationAccountRepository(db).list_owned(user.id, OAUTH_PROVIDER)
    return CalendarIntegrationStatus(
        enabled=settings.calendar_integration_enabled,
        provider=settings.calendar_provider,
        write_enabled=settings.calendar_write_enabled,
        connected_accounts=sum(
            account.status == IntegrationAccountStatus.CONNECTED for account in accounts
        ),
    )


@router.get("/integrations/calendar/accounts", response_model=CalendarAccountsOutput)
def calendar_accounts(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CalendarAccountsOutput:
    accounts = IntegrationAccountRepository(db).list_owned(user.id, OAUTH_PROVIDER)
    return CalendarAccountsOutput(accounts=[_account(value) for value in accounts])


@router.post("/integrations/calendar/connect", response_model=CalendarConnectOutput)
def calendar_connect(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarConnectOutput:
    _require_enabled(settings)
    oauth = GoogleCalendarOAuthClient(settings)
    now = utc_now()
    oauth_state = IntegrationOAuthState(
        user_id=user.id,
        provider=OAUTH_PROVIDER,
        purpose=OAUTH_PURPOSE,
        expires_at=now + timedelta(minutes=settings.calendar_oauth_state_expire_minutes),
    )
    IntegrationOAuthStateRepository(db).add(oauth_state)
    db.flush()
    token = oauth.issue_state(user.id, state_id=oauth_state.id, expires_at=oauth_state.expires_at)
    db.commit()
    return CalendarConnectOutput(authorization_url=oauth.authorization_url(token))


@router.get("/integrations/calendar/callback", response_class=RedirectResponse)
def calendar_callback(
    code: Annotated[str, Query(min_length=1)],
    state_token: Annotated[str, Query(alias="state", min_length=1)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    _require_enabled(settings)
    oauth = GoogleCalendarOAuthClient(settings)
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
        raise CalendarAuthenticationError(INVALID_STATE_MESSAGE)
    db.commit()
    tokens = oauth.exchange_code(code)
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not isinstance(refresh_token, str) or not isinstance(access_token, str):
        raise CalendarAuthenticationError("Google did not return an offline refresh token")
    policy = CalendarPolicy(
        settings.calendar_allowed_account_list,
        settings.calendar_internal_domain_list,
        settings.calendar_max_attendees,
    )
    provider = GoogleCalendarProvider(access_token, settings.calendar_api_timeout_seconds, policy)
    try:
        calendars = provider.list_calendars(250).calendars
    finally:
        provider.close()
    primary = next((item for item in calendars if item.primary), None)
    if primary is None:
        raise CalendarAuthenticationError("Google Calendar primary account was not found")
    address = policy.authorize_account(primary.id)
    repository = IntegrationAccountRepository(db)
    account = repository.get_by_external(claims.user_id, OAUTH_PROVIDER, primary.id)
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    encrypted = store.encrypt({"refresh_token": refresh_token})
    if account is None:
        account = repository.add(
            IntegrationAccount(
                user_id=claims.user_id,
                provider=OAUTH_PROVIDER,
                account_type=IntegrationAccountType.PERSONAL,
                external_account_id=primary.id,
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
        actor_id=claims.user_id,
        event_type="calendar_account_connected",
        resource_type="integration_account",
        resource_id=account.id,
        metadata={"provider": OAUTH_PROVIDER},
        correlation_id=uuid4(),
    )
    db.commit()
    return RedirectResponse(
        url=f"{settings.web_origin_list[0]}/dashboard/integrations/calendar?connected=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/integrations/calendar/disconnect", response_model=CalendarAccountOutput)
def calendar_disconnect(
    value: CalendarDisconnectInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarAccountOutput:
    _require_enabled(settings)
    account = IntegrationAccountRepository(db).get_owned(value.account_id, user.id, OAUTH_PROVIDER)
    if account is None:
        raise CalendarNotFoundError("Calendar account was not found")
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    credentials = store.decrypt(account.encrypted_credentials)
    refresh_token = credentials.get("refresh_token")
    if isinstance(refresh_token, str):
        GoogleCalendarOAuthClient(settings).revoke(refresh_token)
    account.status = IntegrationAccountStatus.REVOKED
    account.encrypted_credentials = store.encrypt({"revoked": True})
    AuditService(db).record(
        actor_type=ActorType.USER,
        actor_id=user.id,
        event_type="calendar_account_disconnected",
        resource_type="integration_account",
        resource_id=account.id,
        metadata={"provider": OAUTH_PROVIDER},
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


def _service(db: Session, settings: Settings) -> CalendarService:
    return CalendarService(
        settings=settings,
        session_factory=sessionmaker(bind=db.get_bind(), expire_on_commit=False),
    )


@router.get("/calendar/calendars", response_model=CalendarListOutput)
def list_calendars(
    account_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=50, ge=1, le=250),
    page_token: str | None = None,
) -> CalendarListOutput:
    return _service(db, settings).list_calendars(
        _context(user.id),
        CalendarListInput(account_id=account_id, limit=limit, page_token=page_token),
    )


@router.get("/calendar/events", response_model=CalendarEventsOutput)
def list_events(
    account_id: UUID,
    calendar_id: str,
    time_min: datetime,
    time_max: datetime,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=50, ge=1, le=250),
    page_token: str | None = None,
    query: str | None = Query(default=None, min_length=1, max_length=500),
) -> CalendarEventsOutput:
    context = _context(user.id)
    service = _service(db, settings)
    common = {
        "account_id": account_id,
        "calendar_id": calendar_id,
        "time_min": time_min,
        "time_max": time_max,
        "limit": limit,
        "page_token": page_token,
    }
    if query:
        return service.search_events(context, CalendarSearchInput(**common, query=query))
    return service.list_events(context, CalendarEventsInput(**common))


@router.get("/calendar/events/{event_id}", response_model=CalendarEventOutput)
def get_event(
    event_id: str,
    account_id: UUID,
    calendar_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarEventOutput:
    return _service(db, settings).get_event(
        _context(user.id),
        CalendarEventInput(account_id=account_id, calendar_id=calendar_id, event_id=event_id),
    )


@router.post("/calendar/availability", response_model=CalendarAvailabilityOutput)
def get_availability(
    value: CalendarAvailabilityInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarAvailabilityOutput:
    return _service(db, settings).get_availability(_context(user.id), value)
