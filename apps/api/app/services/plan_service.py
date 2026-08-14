from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.workflow_enums import CommandStatus
from app.repositories.command_repository import CommandRepository
from app.repositories.plan_repository import PlanRepository
from app.schemas.plan import PlanCreate
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class PlanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.commands = CommandRepository(session)
        self.plans = PlanRepository(session)

    def create(self, command_id: UUID, user_id: UUID, data: PlanCreate) -> Plan:
        command = self.commands.get_owned(command_id, user_id)
        if command is None:
            raise WorkflowNotFoundError("Command not found")
        if self.plans.get_for_command_owned(command_id, user_id) is not None:
            raise WorkflowConflictError("Command already has a plan")

        plan = Plan(command_id=command.id, title=data.title, objective=data.objective)
        self.plans.add(plan)
        if command.status == CommandStatus.PENDING:
            command.status = CommandStatus.PLANNING
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("Command already has a plan") from error
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
