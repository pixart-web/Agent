import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.execution.celery_app import celery_app
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.models.workflow_enums import OutboxStatus
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class CeleryExecutionSender:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or build_tool_registry()

    def send_execution(self, execution_id: UUID, session: Session) -> None:
        execution = ExecutionRepository(session).get_execution(execution_id)
        if execution is None:
            return
        definition = self.registry.get(execution.tool_name, execution.tool_version)
        celery_app.send_task(
            "app.execution.tasks.execute_task_execution",
            args=[str(execution_id)],
            soft_time_limit=definition.timeout_seconds,
            time_limit=definition.timeout_seconds + 5,
        )


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        sender: CeleryExecutionSender | None = None,
        batch_size: int = 50,
        max_attempts: int = 10,
    ) -> None:
        self.session_factory = session_factory
        self.sender = sender or CeleryExecutionSender()
        self.batch_size = batch_size
        self.max_attempts = max_attempts

    def dispatch_once(self) -> int:
        with self.session_factory() as session:
            repository = OutboxRepository(session)
            events = repository.claim_batch(utc_now(), self.batch_size)
            for event in events:
                event.status = OutboxStatus.PROCESSING
                event.attempts += 1
            event_ids = [event.id for event in events]
            session.commit()

        processed = 0
        for event_id in event_ids:
            with self.session_factory() as session:
                repository = OutboxRepository(session)
                event = repository.get_for_update(event_id)
                if event is None or event.status != OutboxStatus.PROCESSING:
                    continue
                try:
                    if event.event_type == "execution.requested":
                        self.sender.send_execution(
                            UUID(str(event.payload["execution_id"])), session
                        )
                    event.status = OutboxStatus.PROCESSED
                    event.processed_at = utc_now()
                    event.last_error = None
                    processed += 1
                except Exception:
                    event.status = OutboxStatus.FAILED
                    event.last_error = "Queue dispatch failed"
                    event.next_attempt_at = (
                        utc_now() + timedelta(seconds=min(300, 2**event.attempts))
                        if event.attempts < self.max_attempts
                        else None
                    )
                    logger.exception(
                        "outbox_dispatch_failed",
                        extra={"event_id": str(event.id), "attempt": event.attempts},
                    )
                session.commit()
        return processed
