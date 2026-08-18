from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.approval_request import ApprovalRequest
from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import (
    ApprovalStatus,
    RiskLevel,
    TaskActionStatus,
    TaskExecutionStatus,
)


class ExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _owned_actions(user_id: UUID) -> Select:
        return (
            select(TaskAction)
            .join(Task, Task.id == TaskAction.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Command.user_id == user_id)
        )

    def add_action(self, action: TaskAction) -> None:
        self.session.add(action)

    def get_action_owned(self, action_id: UUID, user_id: UUID) -> TaskAction | None:
        return self.session.scalar(self._owned_actions(user_id).where(TaskAction.id == action_id))

    def get_action_owned_for_update(self, action_id: UUID, user_id: UUID) -> TaskAction | None:
        return self.session.scalar(
            self._owned_actions(user_id)
            .where(TaskAction.id == action_id)
            .with_for_update(of=TaskAction)
        )

    def list_actions_for_task_owned(self, task_id: UUID, user_id: UUID) -> list[TaskAction]:
        statement = (
            self._owned_actions(user_id)
            .where(TaskAction.task_id == task_id)
            .order_by(TaskAction.created_at, TaskAction.id)
        )
        return list(self.session.scalars(statement))

    def list_actions_for_task(self, task_id: UUID) -> list[TaskAction]:
        statement = (
            select(TaskAction)
            .where(TaskAction.task_id == task_id)
            .order_by(TaskAction.created_at, TaskAction.id)
        )
        return list(self.session.scalars(statement))

    def add_execution(self, execution: TaskExecution) -> None:
        self.session.add(execution)

    def get_execution(self, execution_id: UUID) -> TaskExecution | None:
        return self.session.get(TaskExecution, execution_id)

    def get_execution_for_update(self, execution_id: UUID) -> TaskExecution | None:
        return self.session.scalar(
            select(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .with_for_update(of=TaskExecution)
        )

    def get_execution_owned(self, execution_id: UUID, user_id: UUID) -> TaskExecution | None:
        statement = (
            select(TaskExecution)
            .join(TaskAction, TaskAction.id == TaskExecution.task_action_id)
            .join(Task, Task.id == TaskAction.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(TaskExecution.id == execution_id, Command.user_id == user_id)
        )
        return self.session.scalar(statement)

    def list_executions_for_action_owned(
        self, action_id: UUID, user_id: UUID
    ) -> list[TaskExecution]:
        statement = (
            select(TaskExecution)
            .join(TaskAction, TaskAction.id == TaskExecution.task_action_id)
            .join(Task, Task.id == TaskAction.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(TaskExecution.task_action_id == action_id, Command.user_id == user_id)
            .order_by(TaskExecution.attempt_number, TaskExecution.created_at)
        )
        return list(self.session.scalars(statement))

    def next_attempt(self, action_id: UUID) -> int:
        value = self.session.scalar(
            select(func.max(TaskExecution.attempt_number)).where(
                TaskExecution.task_action_id == action_id
            )
        )
        return (value or 0) + 1

    def add_approval(self, approval: ApprovalRequest) -> None:
        self.session.add(approval)

    def get_approval_owned(self, approval_id: UUID, user_id: UUID) -> ApprovalRequest | None:
        return self.session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.id == approval_id, ApprovalRequest.user_id == user_id
            )
        )

    def get_approval_owned_for_update(
        self, approval_id: UUID, user_id: UUID
    ) -> ApprovalRequest | None:
        return self.session.scalar(
            select(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id, ApprovalRequest.user_id == user_id)
            .with_for_update(of=ApprovalRequest)
        )

    def pending_approval_for_action(self, action_id: UUID) -> ApprovalRequest | None:
        return self.session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.task_action_id == action_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
        )

    def approved_approval_for_action(
        self, action_id: UUID, fingerprint: str
    ) -> ApprovalRequest | None:
        return self.session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.task_action_id == action_id,
                ApprovalRequest.status == ApprovalStatus.APPROVED,
                ApprovalRequest.action_fingerprint == fingerprint,
            )
        )

    def list_approvals_owned(
        self,
        user_id: UUID,
        *,
        status: ApprovalStatus | None,
        risk_level: RiskLevel | None,
        limit: int,
        offset: int,
    ) -> list[ApprovalRequest]:
        statement = select(ApprovalRequest).where(ApprovalRequest.user_id == user_id)
        if status is not None:
            statement = statement.where(ApprovalRequest.status == status)
        if risk_level is not None:
            statement = statement.where(ApprovalRequest.risk_level == risk_level)
        statement = (
            statement.order_by(ApprovalRequest.requested_at.desc(), ApprovalRequest.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def cancel_pending_approvals(self, action_id: UUID, decided_at: datetime) -> None:
        approvals = self.session.scalars(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.task_action_id == action_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
            .with_for_update(of=ApprovalRequest)
        )
        for approval in approvals:
            approval.status = ApprovalStatus.CANCELLED
            approval.decided_at = decided_at

    def active_action_for_task(self, task_id: UUID) -> TaskAction | None:
        return self.session.scalar(
            select(TaskAction).where(
                TaskAction.task_id == task_id,
                TaskAction.status.not_in([TaskActionStatus.COMPLETED, TaskActionStatus.CANCELLED]),
            )
        )

    def list_executions_owned(
        self,
        user_id: UUID,
        *,
        status: TaskExecutionStatus | None,
        agent_id: str | None,
        risk_level: RiskLevel | None,
        limit: int,
        offset: int,
    ) -> list[TaskExecution]:
        statement = (
            select(TaskExecution)
            .join(TaskAction, TaskAction.id == TaskExecution.task_action_id)
            .join(Task, Task.id == TaskAction.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Command.user_id == user_id)
        )
        if status is not None:
            statement = statement.where(TaskExecution.status == status)
        if agent_id is not None:
            statement = statement.where(Task.agent_id == agent_id)
        if risk_level is not None:
            statement = statement.where(TaskAction.risk_level == risk_level)
        statement = (
            statement.order_by(TaskExecution.created_at.desc(), TaskExecution.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))
