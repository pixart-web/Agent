import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.execution.celery_app import celery_app
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.models.automation import AutomationRun
from app.models.workflow_enums import ActorType, OutboxStatus
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.audit_service import AuditService

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


class CeleryAutomationSender:
    def send_planning(
        self, command_id: UUID, user_id: UUID, run_id: UUID, session: Session
    ) -> None:
        del session
        celery_app.send_task(
            "app.automations.tasks.plan_automation_command",
            args=[str(command_id), str(user_id), str(run_id)],
            soft_time_limit=120,
            time_limit=125,
        )


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        sender: CeleryExecutionSender | None = None,
        automation_sender: CeleryAutomationSender | None = None,
        batch_size: int = 50,
        max_attempts: int = 10,
    ) -> None:
        self.session_factory = session_factory
        self.sender = sender or CeleryExecutionSender()
        self.automation_sender = automation_sender or CeleryAutomationSender()
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
                    elif event.event_type == "automation.plan_requested":
                        self.automation_sender.send_planning(
                            UUID(str(event.payload["command_id"])),
                            UUID(str(event.payload["user_id"])),
                            UUID(str(event.payload["run_id"])),
                            session,
                        )
                    else:
                        raise ValueError("Unsupported outbox event type")
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
                    if (
                        event.event_type == "automation.plan_requested"
                        and event.attempts >= self.max_attempts
                    ):
                        run = session.get(AutomationRun, UUID(str(event.payload["run_id"])))
                        owner_id = UUID(str(event.payload["user_id"]))
                        if run is not None and run.user_id == owner_id and run.status == "running":
                            run.status = "failed"
                            run.error_code = "queue_dispatch_failed"
                            run.error_message = "Supervisor queue dispatch exhausted retries"
                            run.completed_at = utc_now()
                            AuditService(session).record(
                                actor_type=ActorType.SYSTEM,
                                actor_id=None,
                                event_type="automation_planning_failed",
                                resource_type="automation_run",
                                resource_id=run.id,
                                metadata={"error_code": run.error_code},
                                correlation_id=run.correlation_id,
                            )
                    logger.exception(
                        "outbox_dispatch_failed",
                        extra={"event_id": str(event.id), "attempt": event.attempts},
                    )
                session.commit()
        return processed
