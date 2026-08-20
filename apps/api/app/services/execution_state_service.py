from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import (
    ActorType,
    CommandStatus,
    PlanStatus,
    TaskStatus,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.task_status_history_repository import TaskStatusHistoryRepository
from app.services.audit_service import AuditService


class ExecutionStateService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.history = TaskStatusHistoryRepository(session)
        self.audit = AuditService(session)
        self.audit_repository = AuditRepository(session)

    def mark_task_running(
        self, task: Task, plan: Plan, command: Command, correlation_id: UUID
    ) -> None:
        now = utc_now()
        previous = task.status
        if task.status != TaskStatus.RUNNING:
            task.status = TaskStatus.RUNNING
            task.started_at = task.started_at or now
            self.history.add(
                TaskStatusHistory(
                    task_id=task.id,
                    from_status=previous,
                    to_status=TaskStatus.RUNNING,
                    changed_by_user_id=None,
                    reason="Execution worker started",
                )
            )
        if plan.status == PlanStatus.READY:
            plan.status = PlanStatus.IN_PROGRESS
        if command.status != CommandStatus.IN_PROGRESS:
            command.status = CommandStatus.IN_PROGRESS

    def complete_task_if_ready(
        self, task: Task, plan: Plan, command: Command, correlation_id: UUID
    ) -> None:
        from app.models.task_action import TaskAction
        from app.models.workflow_enums import TaskActionStatus

        actions = list(
            self.session.scalars(
                select(TaskAction).where(
                    TaskAction.task_id == task.id,
                    TaskAction.status != TaskActionStatus.CANCELLED,
                )
            )
        )
        if not actions or not all(
            action.status == TaskActionStatus.COMPLETED for action in actions
        ):
            return
        previous = task.status
        task.status = TaskStatus.COMPLETED
        task.completed_at = utc_now()
        self.history.add(
            TaskStatusHistory(
                task_id=task.id,
                from_status=previous,
                to_status=TaskStatus.COMPLETED,
                changed_by_user_id=None,
                reason="All required actions completed",
            )
        )
        self.audit.record(
            actor_type=ActorType.WORKER,
            actor_id=None,
            event_type="task_completed",
            resource_type="task",
            resource_id=task.id,
            metadata={"plan_id": str(plan.id)},
            correlation_id=correlation_id,
        )
        self._update_plan_command(plan, command, correlation_id)

    def fail_task(
        self,
        task: Task,
        plan: Plan,
        command: Command,
        correlation_id: UUID,
        reason: str,
    ) -> None:
        previous = task.status
        task.status = TaskStatus.FAILED
        task.completed_at = utc_now()
        task.error_message = reason[:500]
        self.history.add(
            TaskStatusHistory(
                task_id=task.id,
                from_status=previous,
                to_status=TaskStatus.FAILED,
                changed_by_user_id=None,
                reason=reason[:500],
            )
        )
        if command.status != CommandStatus.CANCELLED:
            plan.status = PlanStatus.FAILED
            command.status = CommandStatus.FAILED
            command.completed_at = utc_now()
        self.audit.record(
            actor_type=ActorType.WORKER,
            actor_id=None,
            event_type="task_failed",
            resource_type="task",
            resource_id=task.id,
            metadata={"reason": reason[:200]},
            correlation_id=correlation_id,
        )

    def _update_plan_command(self, plan: Plan, command: Command, correlation_id: UUID) -> None:
        if command.status == CommandStatus.CANCELLED:
            return
        tasks = list(self.session.scalars(select(Task).where(Task.plan_id == plan.id)))
        if tasks and all(task.status == TaskStatus.COMPLETED for task in tasks):
            now = utc_now()
            plan.status = PlanStatus.COMPLETED
            command.status = CommandStatus.COMPLETED
            command.completed_at = now
            self.audit.record(
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                event_type="command_completed",
                resource_type="command",
                resource_id=command.id,
                metadata={"plan_id": str(plan.id)},
                correlation_id=correlation_id,
            )

    def progress(self, plan_id: UUID) -> dict[str, int | float]:
        tasks = list(self.session.scalars(select(Task).where(Task.plan_id == plan_id)))
        total = len(tasks)
        completed = sum(task.status == TaskStatus.COMPLETED for task in tasks)
        failed = sum(task.status == TaskStatus.FAILED for task in tasks)
        running = sum(task.status == TaskStatus.RUNNING for task in tasks)
        waiting = sum(task.status == TaskStatus.WAITING_APPROVAL for task in tasks)
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "waiting_approval_tasks": waiting,
            "progress_percentage": round(completed / total * 100, 2) if total else 0.0,
        }
