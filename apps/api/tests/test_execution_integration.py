import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from redis import Redis
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent import Agent
from app.models.calendar_write_record import CalendarWriteRecord
from app.models.command import Command
from app.models.integration_account import IntegrationAccount
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.outbox_event import OutboxEvent
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.user import User
from app.models.workflow_enums import (
    ActorType,
    CalendarWriteStatus,
    IntegrationAccountStatus,
    IntegrationAccountType,
    OutboxStatus,
    RiskLevel,
)
from app.repositories.integration_oauth_state_repository import (
    IntegrationOAuthStateRepository,
)
from app.repositories.outbox_repository import OutboxRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def integration_url() -> str:
    url = os.getenv("INTEGRATION_DATABASE_URL")
    if not url:
        pytest.skip("INTEGRATION_DATABASE_URL is not configured")
    return url


def test_postgres_row_lock_and_outbox_claim(integration_url: str) -> None:
    engine = create_engine(integration_url)
    event_id = uuid4()
    with Session(engine) as session:
        session.execute(delete(OutboxEvent))
        session.add(
            OutboxEvent(
                id=event_id,
                event_type="execution.requested",
                aggregate_type="task_execution",
                aggregate_id=uuid4(),
                payload={"execution_id": str(uuid4())},
                status=OutboxStatus.PENDING,
            )
        )
        session.commit()

    first = engine.connect()
    first_tx = first.begin()
    first.execute(
        select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update(of=OutboxEvent)
    )
    second = engine.connect()
    second_tx = second.begin()
    with pytest.raises(OperationalError):
        second.execute(
            select(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .with_for_update(of=OutboxEvent, nowait=True)
        )
    second_tx.rollback()
    second.close()
    first_tx.commit()
    first.close()

    with Session(engine) as session:
        claimed = OutboxRepository(session).claim_batch(utc_now(), 10)
        assert [event.id for event in claimed] == [event_id]
        claimed[0].status = OutboxStatus.PROCESSING
        session.commit()
    engine.dispose()


def test_redis_transport_is_reachable() -> None:
    url = os.getenv("INTEGRATION_REDIS_URL")
    if not url:
        pytest.skip("INTEGRATION_REDIS_URL is not configured")
    client = Redis.from_url(url)
    assert client.ping() is True


def test_postgres_oauth_state_atomic_consume_allows_one_winner(integration_url: str) -> None:
    engine = create_engine(integration_url)
    user_id = uuid4()
    state_id = uuid4()
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email=f"oauth-lock-{user_id}@example.com",
                password_hash="not-used",
                full_name="OAuth Lock",
            )
        )
        session.flush()
        session.add(
            IntegrationOAuthState(
                id=state_id,
                user_id=user_id,
                provider="gmail",
                purpose="email_oauth",
                expires_at=utc_now() + timedelta(minutes=5),
            )
        )
        session.commit()

    barrier = Barrier(2)

    def consume() -> bool:
        with Session(engine) as session:
            barrier.wait()
            consumed = IntegrationOAuthStateRepository(session).consume(
                state_id, user_id, "gmail", "email_oauth", utc_now()
            )
            session.commit()
            return consumed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _value: consume(), range(2)))

    assert sorted(results) == [False, True]
    with Session(engine) as session:
        assert session.get(IntegrationOAuthState, state_id).consumed_at is not None
    engine.dispose()


def test_postgres_calendar_write_reservation_allows_one_winner(integration_url: str) -> None:
    engine = create_engine(integration_url)
    user_id = uuid4()
    action_id = uuid4()
    correlation_id = uuid4()
    with Session(engine) as session:
        user = User(
            id=user_id,
            email=f"calendar-lock-{user_id}@example.com",
            password_hash="not-used",
            full_name="Calendar Lock",
        )
        agent = Agent(
            id=f"calendar-{str(user_id)[:8]}",
            name="Calendar Test",
            description="Integration test agent",
        )
        session.add_all([user, agent])
        session.flush()
        command = Command(user_id=user_id, input="Reserve one calendar write")
        session.add(command)
        session.flush()
        plan = Plan(command_id=command.id, title="Calendar", objective="Concurrency")
        session.add(plan)
        session.flush()
        task = Task(
            plan_id=plan.id,
            agent_id=agent.id,
            title="Calendar write",
            instructions="Test the reservation",
            risk_level=RiskLevel.YELLOW,
        )
        session.add(task)
        session.flush()
        action = TaskAction(
            id=action_id,
            task_id=task.id,
            tool_name="calendar.create_event",
            tool_version="1",
            input_payload={"calendar_id": "primary"},
            risk_level=RiskLevel.YELLOW,
            created_by_type=ActorType.AGENT,
            action_fingerprint="a" * 64,
            correlation_id=correlation_id,
        )
        account = IntegrationAccount(
            user_id=user_id,
            provider="google_calendar",
            account_type=IntegrationAccountType.PERSONAL,
            external_account_id=f"calendar-{user_id}@example.com",
            email_address=f"calendar-{user_id}@example.com",
            status=IntegrationAccountStatus.CONNECTED,
            scopes=["calendar.events"],
            encrypted_credentials="test-ciphertext",
        )
        session.add_all([action, account])
        session.commit()
        account_id = account.id

    barrier = Barrier(2)
    provider_calls: list[UUID] = []

    def reserve() -> bool:
        with Session(engine) as session:
            barrier.wait()
            session.scalar(select(TaskAction).where(TaskAction.id == action_id).with_for_update())
            existing = session.scalar(
                select(CalendarWriteRecord).where(CalendarWriteRecord.task_action_id == action_id)
            )
            if existing is not None:
                session.commit()
                return False
            session.add(
                CalendarWriteRecord(
                    user_id=user_id,
                    account_id=account_id,
                    task_action_id=action_id,
                    operation="create",
                    idempotency_key=f"{action_id}:{'a' * 64}",
                    payload_fingerprint="a" * 64,
                    status=CalendarWriteStatus.PENDING,
                    calendar_id="primary",
                )
            )
            session.commit()
            provider_calls.append(action_id)
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _value: reserve(), range(2)))

    assert sorted(results) == [False, True]
    assert provider_calls == [action_id]
    with Session(engine) as session:
        records = session.scalars(
            select(CalendarWriteRecord).where(CalendarWriteRecord.task_action_id == action_id)
        ).all()
        assert len(records) == 1
    engine.dispose()
