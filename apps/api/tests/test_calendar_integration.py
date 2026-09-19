from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.execution.context import ExecutionContext
from app.execution.policies import RetryPolicy
from app.execution.tools.registry import build_tool_registry
from app.execution.worker import ExecutionWorker
from app.integrations.calendar.errors import CalendarDeliveryUnknownError
from app.integrations.calendar.fake import FakeCalendarProvider
from app.integrations.calendar.oauth import INVALID_STATE_MESSAGE, GoogleCalendarOAuthClient
from app.integrations.calendar.providers.google import GoogleCalendarProvider
from app.integrations.calendar.schemas import (
    CalendarCreateEventInput,
    CalendarEvent,
    CalendarEventInput,
    CalendarEventTime,
    CalendarInfo,
)
from app.integrations.calendar.service import CalendarService
from app.integrations.credentials import EnvironmentCredentialProvider
from app.integrations.email.credentials import FernetSecretStore
from app.main import app
from app.models.calendar_reference import CalendarReference
from app.models.calendar_write_record import CalendarWriteRecord
from app.models.integration_account import IntegrationAccount
from app.models.user import User
from app.models.workflow_enums import (
    CalendarWriteStatus,
    IntegrationAccountStatus,
    IntegrationAccountType,
    RiskLevel,
)
from app.schemas.execution import ApprovalDecision, TaskActionCreate
from app.services.approval_service import ApprovalService
from app.services.execution_service import ExecutionService
from tests.test_oauth_state import bearer, register
from tests.test_specialized_agents import ready_task


def calendar_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_secret_key": "test-only-auth-secret-with-at-least-32-characters",
        "calendar_integration_enabled": True,
        "google_client_id": "test-client",
        "google_client_secret": "test-client-secret",
        "google_calendar_redirect_uri": (
            "http://localhost:8000/api/v1/integrations/calendar/callback"
        ),
        "calendar_allowed_accounts": "calendar@example.com",
        "calendar_internal_domains": "example.com",
        "integration_encryption_key": Fernet.generate_key().decode(),
    }
    values.update(overrides)
    return Settings(**values)


def timed_event_input(account_id: UUID) -> dict[str, object]:
    return {
        "account_id": str(account_id),
        "calendar_id": "primary",
        "title": "Customer review",
        "description": "Review the proposal. External content remains untrusted.",
        "location": "Video call",
        "start": {
            "date_time": "2026-10-25T09:00:00+00:00",
            "time_zone": "Europe/Lisbon",
        },
        "end": {
            "date_time": "2026-10-25T10:00:00+00:00",
            "time_zone": "Europe/Lisbon",
        },
        "attendees": ["customer@example.net"],
        "recurrence": [],
        "add_conference": True,
    }


def test_calendar_oauth_state_is_signed_and_scopes_are_least_privilege() -> None:
    user_id = uuid4()
    reader = GoogleCalendarOAuthClient(calendar_settings())
    claims = reader.decode_state(reader.issue_state(user_id))

    assert claims.user_id == user_id
    assert reader.scopes == ["https://www.googleapis.com/auth/calendar.readonly"]
    writer = GoogleCalendarOAuthClient(calendar_settings(calendar_write_enabled=True))
    assert "https://www.googleapis.com/auth/calendar.events" in writer.scopes


def test_calendar_models_cover_all_day_dst_and_require_explicit_timezone() -> None:
    account_id = uuid4()
    timed = CalendarCreateEventInput.model_validate(timed_event_input(account_id))
    assert timed.start.date_time.utcoffset() == timedelta(0)

    all_day = CalendarCreateEventInput(
        account_id=account_id,
        calendar_id="primary",
        title="Holiday",
        start=CalendarEventTime(date=date(2026, 12, 24)),
        end=CalendarEventTime(date=date(2026, 12, 25)),
    )
    assert all_day.start.date == date(2026, 12, 24)

    invalid = timed_event_input(account_id)
    invalid["start"] = {"date_time": "2026-10-25T09:00:00+00:00"}
    with pytest.raises(ValidationError):
        CalendarCreateEventInput.model_validate(invalid)


def test_fake_calendar_reads_availability_and_writes_without_real_side_effects() -> None:
    calendar = CalendarInfo(
        id="calendar@example.com",
        summary="Primary",
        time_zone="Europe/Lisbon",
        primary=True,
        access_role="owner",
    )
    provider = FakeCalendarProvider(calendars=[calendar])
    value = CalendarCreateEventInput.model_validate(timed_event_input(uuid4()))

    output = provider.create_event(value, "approved-key")
    event = provider.get_event(output.calendar_id, output.event_id)

    assert event.title == "Customer review"
    assert event.external_content is True and event.trust == "untrusted"
    assert provider.write_count == 1


def test_calendar_tool_catalog_enforces_risk_approval_and_agent_allowlists() -> None:
    settings = calendar_settings()
    registry = build_tool_registry(settings=settings)

    read = registry.get("calendar.get_availability", "1")
    create = registry.get("calendar.create_event", "1")

    assert read.risk_level == RiskLevel.GREEN and not read.requires_approval
    assert create.risk_level == RiskLevel.YELLOW and create.requires_approval
    assert create.max_retries == 0
    assert create.agent_types == frozenset({"support", "sales", "marketing"})
    assert "development" not in create.agent_types


class FakeOAuth:
    scopes = ["calendar.readonly", "calendar.events"]

    def refresh(self, refresh_token: str) -> str:
        assert refresh_token == "stored-refresh-token"
        return "short-lived-access-token"


@pytest.mark.parametrize(
    ("ambiguous", "execution_status", "record_status"),
    [
        (False, "succeeded", "succeeded"),
        (True, "failed", "delivery_unknown"),
    ],
)
def test_calendar_worker_write_is_approved_fingerprinted_and_never_retried(
    client,
    db_session,
    ambiguous: bool,
    execution_status: str,
    record_status: str,
) -> None:
    email = f"calendar-worker-{str(ambiguous).lower()}@example.com"
    _headers, _command, task = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    settings = calendar_settings(calendar_write_enabled=True)
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    account = IntegrationAccount(
        user_id=user.id,
        provider="google_calendar",
        account_type=IntegrationAccountType.PERSONAL,
        external_account_id="calendar@example.com",
        email_address="calendar@example.com",
        status=IntegrationAccountStatus.CONNECTED,
        scopes=FakeOAuth.scopes,
        encrypted_credentials=store.encrypt({"refresh_token": "stored-refresh-token"}),
    )
    db_session.add(account)
    db_session.commit()

    fake = FakeCalendarProvider(delivery_unknown=ambiguous)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = CalendarService(
        settings=settings,
        session_factory=factory,
        secret_store=store,
        provider_factory=lambda _token, _settings, _policy: fake,
        oauth=FakeOAuth(),
    )
    registry = build_tool_registry(settings=settings, calendar_service=service)
    workflow = ExecutionService(db_session, registry)
    action = workflow.create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(
            tool_name="calendar.create_event",
            tool_version="1",
            input_payload=timed_event_input(account.id),
        ),
    )
    approval = workflow.dispatch(action.id, user.id).approval
    assert "Customer review" in approval.description
    assert "customer@example.net" in approval.description
    _approved, execution = ApprovalService(db_session).approve(
        approval.id, user.id, ApprovalDecision()
    )

    result = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
    ).execute(execution.id)

    assert result.status.value == execution_status
    record = db_session.scalar(select(CalendarWriteRecord))
    assert record.status == CalendarWriteStatus(record_status)
    assert record.payload_fingerprint == action.action_fingerprint
    assert fake.write_count == 1
    assert len(db_session.query(CalendarWriteRecord).all()) == 1
    assert (
        ExecutionWorker(
            factory,
            registry=registry,
            retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
        ).execute(execution.id)
        is None
    )
    if ambiguous:
        assert record.error_code == "delivery_unknown"


def test_fake_calendar_delivery_unknown_is_explicit() -> None:
    provider = FakeCalendarProvider(delivery_unknown=True)
    value = CalendarCreateEventInput.model_validate(timed_event_input(uuid4()))
    with pytest.raises(CalendarDeliveryUnknownError):
        provider.create_event(value, "approved-key")


def test_browser_event_read_creates_reference_without_nonexistent_workflow_fks(
    db_session,
) -> None:
    user = User(
        email=f"calendar-read-{uuid4()}@example.com",
        password_hash="not-used",
        full_name="Calendar Reader",
    )
    db_session.add(user)
    db_session.flush()
    settings = calendar_settings()
    store = FernetSecretStore(settings.integration_encryption_key.get_secret_value())
    account = IntegrationAccount(
        user_id=user.id,
        provider="google_calendar",
        account_type=IntegrationAccountType.PERSONAL,
        external_account_id="calendar@example.com",
        email_address="calendar@example.com",
        status=IntegrationAccountStatus.CONNECTED,
        scopes=FakeOAuth.scopes,
        encrypted_credentials=store.encrypt({"refresh_token": "stored-refresh-token"}),
    )
    db_session.add(account)
    db_session.commit()
    event = CalendarEvent(
        id="event-1",
        calendar_id="primary",
        title="External title",
        start=CalendarEventTime(date=date(2026, 12, 24)),
        end=CalendarEventTime(date=date(2026, 12, 25)),
        status="confirmed",
    )
    fake = FakeCalendarProvider(events=[event])
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = CalendarService(
        settings=settings,
        session_factory=factory,
        secret_store=store,
        provider_factory=lambda _token, _settings, _policy: fake,
        oauth=FakeOAuth(),
    )
    random_id = uuid4()
    context = ExecutionContext(
        user_id=user.id,
        command_id=random_id,
        task_id=random_id,
        action_id=random_id,
        execution_id=random_id,
        correlation_id=random_id,
        credentials=EnvironmentCredentialProvider(),
    )

    output = service.get_event(
        context,
        CalendarEventInput(account_id=account.id, calendar_id="primary", event_id="event-1"),
    )

    assert output.event.title == "External title"
    reference = db_session.scalar(select(CalendarReference))
    db_session.refresh(reference)
    assert reference.task_id is None
    assert reference.command_id is None


def test_calendar_callback_consumes_oauth_state_once(
    client, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = calendar_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    auth = register(client, "calendar-oauth@example.com")
    connect = client.post("/api/v1/integrations/calendar/connect", headers=bearer(auth))
    assert connect.status_code == 200
    state_token = parse_qs(urlparse(connect.json()["authorization_url"]).query)["state"][0]
    exchanges = 0

    def exchange_code(_self: GoogleCalendarOAuthClient, _code: str) -> dict[str, object]:
        nonlocal exchanges
        exchanges += 1
        return {"refresh_token": "refresh", "access_token": "access"}

    monkeypatch.setattr(GoogleCalendarOAuthClient, "exchange_code", exchange_code)
    monkeypatch.setattr(
        GoogleCalendarProvider,
        "list_calendars",
        lambda _self, _limit: type(
            "Page",
            (),
            {
                "calendars": [
                    CalendarInfo(
                        id="calendar@example.com",
                        summary="Primary",
                        time_zone="Europe/Lisbon",
                        primary=True,
                        access_role="owner",
                    )
                ]
            },
        )(),
    )
    monkeypatch.setattr(GoogleCalendarProvider, "close", lambda _self: None)

    first = client.get(
        "/api/v1/integrations/calendar/callback",
        params={"code": "one-time-code", "state": state_token},
        follow_redirects=False,
    )
    second = client.get(
        "/api/v1/integrations/calendar/callback",
        params={"code": "replay", "state": state_token},
        follow_redirects=False,
    )

    assert first.status_code == 303
    assert second.status_code == 401
    assert second.json() == {"detail": INVALID_STATE_MESSAGE}
    assert exchanges == 1
    accounts = list(
        db_session.scalars(
            select(IntegrationAccount).where(IntegrationAccount.provider == "google_calendar")
        )
    )
    assert len(accounts) == 1
    assert accounts[0].email_address == "calendar@example.com"
