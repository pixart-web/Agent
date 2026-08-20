from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.plan import Plan
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import (
    TERMINAL_COMMAND_STATUSES,
    CommandStatus,
    PlanStatus,
    TaskStatus,
)
from app.repositories.command_repository import CommandRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.task_status_history_repository import TaskStatusHistoryRepository
from app.schemas.plan import PlanCreate
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class PlanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.commands = CommandRepository(session)
        self.plans = PlanRepository(session)
        self.tasks = TaskRepository(session)
        self.history = TaskStatusHistoryRepository(session)

    def create(self, command_id: UUID, user_id: UUID, data: PlanCreate) -> Plan:
        try:
            command = self.commands.get_owned_for_update(command_id, user_id)
            if command is None:
                raise WorkflowNotFoundError("Command not found")
            if command.status in TERMINAL_COMMAND_STATUSES:
                raise WorkflowConflictError("A terminal command cannot receive a plan")
            if self.plans.get_for_command_owned(command_id, user_id) is not None:
                raise WorkflowConflictError("Command already has a plan")

            plan = Plan(
                command_id=command.id,
                title=data.title,
                objective=data.objective,
                version=self.plans.next_version(command.id),
                is_current=True,
            )
            self.plans.add(plan)
            if command.status == CommandStatus.PENDING:
                command.status = CommandStatus.PLANNING
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("Command already has a plan") from error
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(plan)
        return plan

    def get_for_command_owned(self, command_id: UUID, user_id: UUID) -> Plan:
        if self.commands.get_owned(command_id, user_id) is None:
            raise WorkflowNotFoundError("Command not found")
        plan = self.plans.get_for_command_owned(command_id, user_id)
        if plan is None:
            raise WorkflowNotFoundError("Plan not found")
        return plan

    def get_owned(self, plan_id: UUID, user_id: UUID) -> Plan:
        plan = self.plans.get_owned(plan_id, user_id)
        if plan is None:
            raise WorkflowNotFoundError("Plan not found")
        return plan

    def list_for_command_owned(self, command_id: UUID, user_id: UUID) -> list[Plan]:
        if self.commands.get_owned(command_id, user_id) is None:
            raise WorkflowNotFoundError("Command not found")
        return self.plans.list_for_command_owned(command_id, user_id)

    def approve(self, plan_id: UUID, user_id: UUID) -> Plan:
        try:
            plan_and_command = self.plans.get_owned_with_command_for_update(plan_id, user_id)
            if plan_and_command is None:
                raise WorkflowNotFoundError("Plan not found")
            plan, command = plan_and_command
            if not plan.is_current or plan.status != PlanStatus.DRAFT:
                raise WorkflowConflictError("Only the current draft plan can be approved")
            if command.status != CommandStatus.PLANNING:
                raise WorkflowConflictError("Command is not waiting for plan approval")
            tasks = self.tasks.list_for_plan_owned_for_update(plan.id, user_id)
            if not tasks:
                raise WorkflowConflictError("A plan without tasks cannot be approved")
            now = utc_now()
            for task in tasks:
                if task.status != TaskStatus.PENDING:
                    raise WorkflowConflictError("Plan contains a task that is not pending")
                task.status = TaskStatus.READY
                self.history.add(
                    TaskStatusHistory(
                        task_id=task.id,
                        from_status=TaskStatus.PENDING,
                        to_status=TaskStatus.READY,
                        changed_by_user_id=user_id,
                        reason="Plan approved",
                    )
                )
            plan.status = PlanStatus.READY
            plan.approved_at = now
            plan.approved_by_user_id = user_id
            command.status = CommandStatus.IN_PROGRESS
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(plan)
        return plan

    def reject(self, plan_id: UUID, user_id: UUID, reason: str) -> Plan:
        try:
            plan_and_command = self.plans.get_owned_with_command_for_update(plan_id, user_id)
            if plan_and_command is None:
                raise WorkflowNotFoundError("Plan not found")
            plan, command = plan_and_command
            if not plan.is_current or plan.status != PlanStatus.DRAFT:
                raise WorkflowConflictError("Only the current draft plan can be rejected")
            now = utc_now()
            for task in self.tasks.list_for_plan_owned_for_update(plan.id, user_id):
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = now
                    self.history.add(
                        TaskStatusHistory(
                            task_id=task.id,
                            from_status=TaskStatus.PENDING,
                            to_status=TaskStatus.CANCELLED,
                            changed_by_user_id=user_id,
                            reason=reason,
                        )
                    )
            plan.status = PlanStatus.CANCELLED
            plan.is_current = False
            plan.rejection_reason = reason
            command.status = CommandStatus.PENDING
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(plan)
        return plan
