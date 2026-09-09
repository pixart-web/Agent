import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from redis import Redis
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.outbox_event import OutboxEvent
from app.models.user import User
from app.models.workflow_enums import OutboxStatus
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
