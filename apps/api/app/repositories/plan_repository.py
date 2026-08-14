from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, plan: Plan) -> None:
        self.session.add(plan)

    def get_for_command_owned(
        self,
        command_id: UUID,
        user_id: UUID,
    ) -> Plan | None:
        statement = (
            select(Plan)
            .join(Command, Command.id == Plan.command_id)
            .where(Plan.command_id == command_id, Command.user_id == user_id)
        )
        return self.session.scalar(statement)

    def get_owned(self, plan_id: UUID, user_id: UUID) -> Plan | None:
        statement = (
            select(Plan)
            .join(Command, Command.id == Plan.command_id)
            .where(Plan.id == plan_id, Command.user_id == user_id)
        )
        return self.session.scalar(statement)
