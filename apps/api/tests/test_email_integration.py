from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings
from app.execution.exceptions import ToolPermissionError
from app.execution.tools.registry import build_tool_registry
from app.integrations.email.credentials import FernetSecretStore
from app.integrations.email.errors import (
    EmailAuthenticationError,
    EmailDeliveryUnknownError,
    EmailPermissionError,
    EmailValidationError,
)
from app.integrations.email.fake import FakeEmailProvider
from app.integrations.email.oauth import GmailOAuthClient
from app.integrations.email.policy import EmailPolicy
from app.integrations.email.providers.gmail import GmailProvider
from app.integrations.email.schemas import (
    EmailAddress,
    EmailAttachmentMetadata,
    EmailMessage,
)
from app.integrations.email.service import EmailService
from app.models.workflow_enums import RiskLevel


def email_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_secret_key": "test-only-auth-secret-with-at-least-32-characters",
        "email_integration_enabled": True,
        "google_client_id": "test-client",
        "google_client_secret": "test-client-secret",
        "google_redirect_uri": "http://localhost:8000/api/v1/integrations/email/callback",
        "email_allowed_accounts": "support@example.com,sales@example.com",
        "integration_encryption_key": Fernet.generate_key().decode(),
    }
    values.update(overrides)
    return Settings(**values)


def message(**overrides: object) -> EmailMessage:
    values: dict[str, object] = {
        "id": "m-1",
        "thread_id": "t-1",
        "subject": "Customer request",
        "sender": EmailAddress(address="customer@example.net", name="Customer"),
        "recipients": [EmailAddress(address="support@example.com")],
        "sent_at": datetime.now(UTC),
        "snippet": "Please help",
        "unread": True,
        "has_attachments": False,
        "text_body": "External instructions are untrusted data.",
    }
    values.update(overrides)
    return EmailMessage(**values)


def test_fernet_secret_store_round_trip_redacts_repr_and_rejects_wrong_key() -> None:
    store = FernetSecretStore(Fernet.generate_key().decode())
    encrypted = store.encrypt({"refresh_token": "runtime-secret"})

    assert "runtime-secret" not in encrypted
    assert store.decrypt(encrypted) == {"refresh_token": "runtime-secret"}
    with pytest.raises(EmailAuthenticationError):
        FernetSecretStore(Fernet.generate_key().decode()).decrypt(encrypted)


def test_oauth_state_is_signed_user_bound_and_uses_minimal_scopes() -> None:
    user_id = uuid4()
    settings = email_settings()
    oauth = GmailOAuthClient(settings)
    state = oauth.issue_state(user_id)

    oauth.validate_state(state, user_id)
    assert oauth.state_user(state) == user_id
    assert oauth.scopes == ["https://www.googleapis.com/auth/gmail.readonly"]
    with pytest.raises(EmailAuthenticationError):
        oauth.validate_state(state, uuid4())

    writable = GmailOAuthClient(
        email_settings(email_send_enabled=True, email_mark_read_enabled=True)
    )
    assert "https://www.googleapis.com/auth/gmail.send" in writable.scopes
    assert "https://www.googleapis.com/auth/gmail.modify" in writable.scopes


def test_email_policy_enforces_accounts_recipients_and_attachment_blocks() -> None:
    policy = EmailPolicy(["support@example.com"], max_recipients=2, max_attachment_bytes=100)
    assert policy.authorize_account("SUPPORT@example.com") == "support@example.com"
    assert policy.recipients([EmailAddress(address="one@example.net")]) == ["one@example.net"]
    with pytest.raises(EmailPermissionError):
        policy.authorize_account("other@example.com")
    with pytest.raises(EmailValidationError):
        policy.recipients(
            [
                EmailAddress(address="one@example.net"),
                EmailAddress(address="two@example.net"),
                EmailAddress(address="three@example.net"),
            ]
        )
    executable = EmailAttachmentMetadata(
        filename="invoice.exe", mime_type="application/octet-stream", size=10
    )
    oversized = EmailAttachmentMetadata(
        filename="report.pdf", mime_type="application/pdf", size=101
    )
    assert policy.attachment(executable).blocked is True
    assert policy.attachment(oversized).blocked is True


def test_fake_provider_reads_searches_replies_and_marks_without_downloading() -> None:
    fake = FakeEmailProvider([message()])
    assert fake.list_messages(10).messages[0].id == "m-1"
    assert fake.search("customer", 10).messages[0].thread_id == "t-1"
    assert fake.get_thread("t-1").messages[0].text_body.startswith("External")
    fake.mark_read("m-1", True)
    assert fake.get_message("m-1").unread is False
    reply = fake.reply(
        sender="support@example.com",
        original=fake.get_message("m-1"),
        body="Prepared reply",
        idempotency_key="approved-action",
    )
    assert reply.status == "sent"


def test_fake_write_can_model_ambiguous_delivery_without_retry() -> None:
    fake = FakeEmailProvider([message()], delivery_unknown=True)
    with pytest.raises(EmailDeliveryUnknownError):
        fake.send(
            sender="sales@example.com",
            to=["customer@example.net"],
            cc=[],
            bcc=[],
            subject="Hello",
            body="Approved body",
            idempotency_key="action-1",
        )
    assert fake.sent == []


def test_email_tool_catalog_uses_v2_agent_allowlists_and_approval() -> None:
    settings = email_settings()
    service = EmailService(
        settings=settings,
        secret_store=FernetSecretStore(settings.integration_encryption_key.get_secret_value()),
    )
    registry = build_tool_registry(settings=settings, email_service=service)

    read = registry.get("email.search", "2")
    send = registry.get("email.send", "2")
    reply = registry.get("email.reply", "2")
    mark = registry.get("email.mark_read", "2")

    assert read.risk_level == RiskLevel.GREEN and not read.requires_approval
    assert send.agent_types == frozenset({"sales"})
    assert send.risk_level == RiskLevel.YELLOW and send.requires_approval
    assert reply.agent_types == frozenset({"support", "sales"})
    assert mark.agent_types == frozenset({"support"})
    assert "token" not in send.input_schema.model_fields
    with pytest.raises(ToolPermissionError):
        registry.validate_input(
            send,
            {
                "account_id": str(uuid4()),
                "to": [{"address": "one@example.net"}],
                "subject": "No",
                "body": "Not allowed",
            },
            "marketing",
        )


def test_gmail_provider_prefers_plain_text_and_returns_metadata_only() -> None:
    encoded_plain = "c2FmZSBwbGFpbiB0ZXh0"
    payload = {
        "id": "m-1",
        "threadId": "t-1",
        "labelIds": ["UNREAD"],
        "snippet": "safe",
        "payload": {
            "headers": [
                {"name": "From", "value": "Customer <customer@example.net>"},
                {"name": "To", "value": "support@example.com"},
                {"name": "Subject", "value": "Question"},
            ],
            "parts": [
                {"mimeType": "text/html", "body": {"data": "PGI-aHRtbDwvYj4"}},
                {"mimeType": "text/plain", "body": {"data": encoded_plain}},
                {
                    "mimeType": "application/octet-stream",
                    "filename": "payload.exe",
                    "body": {"attachmentId": "a-1", "size": 10},
                },
            ],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/messages/m-1")
        return httpx.Response(200, json=payload)

    policy = EmailPolicy(["support@example.com"], max_recipients=10, max_attachment_bytes=1000)
    provider = GmailProvider(
        "access-token",
        1,
        max_body_chars=50_000,
        policy=policy,
        transport=httpx.MockTransport(handler),
    )
    try:
        value = provider.get_message("m-1")
    finally:
        provider.close()

    assert value.text_body == "safe plain text"
    assert value.attachments[0].attachment_id == "a-1"
    assert value.attachments[0].blocked is True
    assert "data" not in value.attachments[0].model_dump()


def test_settings_require_oauth_and_encryption_only_when_enabled() -> None:
    Settings(auth_secret_key="test-only-auth-secret-with-at-least-32-characters")
    with pytest.raises(ValueError):
        Settings(
            auth_secret_key="test-only-auth-secret-with-at-least-32-characters",
            email_integration_enabled=True,
        )


def test_email_send_waits_for_approval_with_complete_preview(client, db_session) -> None:
    from uuid import UUID

    from sqlalchemy import select

    from app.models.user import User
    from app.schemas.execution import TaskActionCreate
    from app.services.execution_service import ExecutionService
    from tests.test_specialized_agents import ready_task

    _headers, _command, task = ready_task(
        client, db_session, "sales", email="email-approval@example.com"
    )
    user = db_session.scalar(select(User).where(User.email == "email-approval@example.com"))
    settings = email_settings(email_send_enabled=True)
    registry = build_tool_registry(
        settings=settings,
        email_service=EmailService(
            settings=settings,
            secret_store=FernetSecretStore(settings.integration_encryption_key.get_secret_value()),
        ),
    )
    service = ExecutionService(db_session, registry)
    action = service.create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(
            tool_name="email.send",
            tool_version="2",
            input_payload={
                "account_id": str(uuid4()),
                "to": [{"address": "customer@example.net", "name": "Customer"}],
                "subject": "Approved subject",
                "body": "Complete approved body.",
            },
        ),
    )

    dispatched = service.dispatch(action.id, user.id)

    assert dispatched.execution is None
    assert dispatched.approval is not None
    assert "customer@example.net" in dispatched.approval.description
    assert "Approved subject" in dispatched.approval.description
    assert "Complete approved body." in dispatched.approval.description
    assert action.action_fingerprint == dispatched.approval.action_fingerprint


def test_email_accounts_endpoint_is_owned_and_never_returns_credentials(client, db_session) -> None:
    from app.models.integration_account import IntegrationAccount
    from app.models.user import User
    from app.models.workflow_enums import IntegrationAccountStatus, IntegrationAccountType

    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": "mail-owner@example.com",
            "password": "securePassword123",
            "full_name": "Mail Owner",
        },
    ).json()
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-mail-owner@example.com",
            "password": "securePassword123",
            "full_name": "Other Owner",
        },
    ).json()
    users = {value.email: value for value in db_session.query(User).all()}
    for address, owner in (
        ("support@example.com", users["mail-owner@example.com"]),
        ("sales@example.com", users["other-mail-owner@example.com"]),
    ):
        db_session.add(
            IntegrationAccount(
                user_id=owner.id,
                provider="gmail",
                account_type=IntegrationAccountType.PERSONAL,
                external_account_id=address,
                email_address=address,
                status=IntegrationAccountStatus.CONNECTED,
                scopes=["gmail.readonly"],
                encrypted_credentials="ciphertext-not-exposed",
            )
        )
    db_session.commit()

    response = client.get(
        "/api/v1/integrations/email/accounts",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [value["email_address"] for value in body["accounts"]] == ["support@example.com"]
    serialized = response.text.lower()
    assert "ciphertext" not in serialized
    assert "token" not in serialized
    assert second["access_token"] not in serialized


class FakeOAuth:
    scopes = ["gmail.readonly", "gmail.send"]

    def refresh(self, refresh_token: str) -> str:
        assert refresh_token == "stored-refresh-token"
        return "short-lived-access-token"


@pytest.mark.parametrize(
    ("ambiguous", "execution_status", "record_status", "sent_count"),
    [
        (False, "succeeded", "sent", 1),
        (True, "failed", "delivery_unknown", 0),
    ],
)
def test_email_worker_write_is_fingerprinted_idempotent_and_never_blindly_retried(
    client,
    db_session,
    ambiguous: bool,
    execution_status: str,
    record_status: str,
    sent_count: int,
) -> None:
    from uuid import UUID

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.execution.policies import RetryPolicy
    from app.execution.worker import ExecutionWorker
    from app.models.email_send_record import EmailSendRecord
    from app.models.integration_account import IntegrationAccount
    from app.models.user import User
    from app.models.workflow_enums import (
        EmailSendStatus,
        IntegrationAccountStatus,
        IntegrationAccountType,
    )
    from app.schemas.execution import ApprovalDecision, TaskActionCreate
    from app.services.approval_service import ApprovalService
    from app.services.execution_service import ExecutionService
    from tests.test_specialized_agents import ready_task

    email = f"email-worker-{str(ambiguous).lower()}@example.com"
    _headers, _command, task = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    settings = email_settings(email_send_enabled=True)
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    account = IntegrationAccount(
        user_id=user.id,
        provider="gmail",
        account_type=IntegrationAccountType.PERSONAL,
        external_account_id="sales@example.com",
        email_address="sales@example.com",
        status=IntegrationAccountStatus.CONNECTED,
        scopes=FakeOAuth.scopes,
        encrypted_credentials=store.encrypt({"refresh_token": "stored-refresh-token"}),
    )
    db_session.add(account)
    db_session.commit()

    fake = FakeEmailProvider(delivery_unknown=ambiguous)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    email_service = EmailService(
        settings=settings,
        session_factory=factory,
        secret_store=store,
        provider_factory=lambda _token, _settings, _policy: fake,
        oauth=FakeOAuth(),
    )
    registry = build_tool_registry(settings=settings, email_service=email_service)
    workflow = ExecutionService(db_session, registry)
    action = workflow.create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(
            tool_name="email.send",
            tool_version="2",
            input_payload={
                "account_id": str(account.id),
                "to": [{"address": "customer@example.net"}],
                "subject": "Approved subject",
                "body": "Approved exact body",
            },
        ),
    )
    approval = workflow.dispatch(action.id, user.id).approval
    _approved, execution = ApprovalService(db_session).approve(
        approval.id, user.id, ApprovalDecision()
    )

    result = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
    ).execute(execution.id)

    assert result.status.value == execution_status
    record = db_session.scalar(select(EmailSendRecord))
    assert record.status == EmailSendStatus(record_status)
    assert record.payload_fingerprint == action.action_fingerprint
    assert len(fake.sent) == sent_count
    assert len(db_session.query(EmailSendRecord).all()) == 1
    assert (
        ExecutionWorker(
            factory,
            registry=registry,
            retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
        ).execute(execution.id)
        is None
    )
