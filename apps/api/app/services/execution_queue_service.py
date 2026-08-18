from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.execution.context_safety import sanitize_execution_payload
from app.models.outbox_event import OutboxEvent
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import (
    ActorType,
    TaskActionStatus,
    TaskExecutionStatus,
)
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.audit_service import AuditService


class ExecutionQueueService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.executions = ExecutionRepository(session)
        self.outbox = OutboxRepository(session)
        self.audit = AuditService(session)

    def queue(
        self,
        *,
        action: TaskAction,
        task: Task,
        actor_type: ActorType,
        actor_id: UUID | None,
    ) -> TaskExecution:
        now = utc_now()
        execution = TaskExecution(
            task_id=task.id,
            task_action_id=action.id,
            attempt_number=self.executions.next_attempt(action.id),
            status=TaskExecutionStatus.QUEUED,
            tool_name=action.tool_name,
            tool_version=action.tool_version,
            input_payload=sanitize_execution_payload(action.input_payload),
            queued_at=now,
            correlation_id=action.correlation_id,
        )
        self.executions.add_execution(execution)
        self.session.flush()
        action.status = TaskActionStatus.QUEUED
        self.outbox.add(
            OutboxEvent(
                event_type="execution.requested",
                aggregate_type="task_execution",
                aggregate_id=execution.id,
                payload={
                    "execution_id": str(execution.id),
                    "correlation_id": str(action.correlation_id),
                },
            )
        )
        self.audit.record(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type="execution_queued",
            resource_type="task_execution",
            resource_id=execution.id,
            metadata={
                "task_id": str(task.id),
                "action_id": str(action.id),
                "attempt": execution.attempt_number,
                "tool": action.tool_name,
            },
            correlation_id=action.correlation_id,
        )
        return execution
