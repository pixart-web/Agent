from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.approval_request import ApprovalRequest
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import (
    ActorType,
    AgentRunStatus,
    ApprovalStatus,
    PlanStatus,
    TaskActionStatus,
    TaskExecutionStatus,
    TaskStatus,
)
from app.repositories.task_status_history_repository import TaskStatusHistoryRepository
from app.services.audit_service import AuditService


class ExecutionCancellationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.history = TaskStatusHistoryRepository(session)
        self.audit = AuditService(session)

    def cancel_for_command(self, command_id: UUID, user_id: UUID) -> None:
        plans = list(
            self.session.scalars(
                select(Plan).where(Plan.command_id == command_id).with_for_update(of=Plan)
            )
        )
        for plan in plans:
            if plan.status not in {
                PlanStatus.COMPLETED,
                PlanStatus.FAILED,
                PlanStatus.CANCELLED,
            }:
                plan.status = PlanStatus.CANCELLED
            tasks = list(
                self.session.scalars(
                    select(Task).where(Task.plan_id == plan.id).with_for_update(of=Task)
                )
            )
            for task in tasks:
                self._cancel_task(task, user_id)

    def _cancel_task(self, task: Task, user_id: UUID) -> None:
        active_runs = self.session.scalars(
            select(AgentRun)
            .where(
                AgentRun.task_id == task.id,
                AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
            )
            .with_for_update(of=AgentRun)
        )
        for run in active_runs:
            run.status = AgentRunStatus.CANCELLED
            run.error_code = "command_cancelled"
            run.error_message = "Command cancelled during agent analysis"
            run.completed_at = utc_now()
            self.audit.record(
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                event_type="agent_run_cancelled",
                resource_type="agent_run",
                resource_id=run.id,
                metadata={"task_id": str(task.id), "agent_id": run.agent_id},
                correlation_id=run.correlation_id,
            )
        actions = list(
            self.session.scalars(
                select(TaskAction)
                .where(TaskAction.task_id == task.id)
                .with_for_update(of=TaskAction)
            )
        )
        has_running = False
        for action in actions:
            if action.status == TaskActionStatus.RUNNING:
                has_running = True
                continue
            if action.status not in {
                TaskActionStatus.COMPLETED,
                TaskActionStatus.FAILED,
                TaskActionStatus.CANCELLED,
            }:
                action.status = TaskActionStatus.CANCELLED
            approvals = self.session.scalars(
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.task_action_id == action.id,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
                .with_for_update(of=ApprovalRequest)
            )
            for approval in approvals:
                approval.status = ApprovalStatus.CANCELLED
                approval.decided_at = utc_now()
            executions = self.session.scalars(
                select(TaskExecution)
                .where(
                    TaskExecution.task_action_id == action.id,
                    TaskExecution.status.in_(
                        [
                            TaskExecutionStatus.CREATED,
                            TaskExecutionStatus.QUEUED,
                            TaskExecutionStatus.RETRY_SCHEDULED,
                            TaskExecutionStatus.WAITING_APPROVAL,
                        ]
                    ),
                )
                .with_for_update(of=TaskExecution)
            )
            for execution in executions:
                execution.status = TaskExecutionStatus.CANCELLED
                execution.completed_at = utc_now()
        if not has_running and task.status not in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            previous = task.status
            task.status = TaskStatus.CANCELLED
            task.completed_at = utc_now()
            self.history.add(
                TaskStatusHistory(
                    task_id=task.id,
                    from_status=previous,
                    to_status=TaskStatus.CANCELLED,
                    changed_by_user_id=user_id,
                    reason="Command cancelled",
                )
            )
