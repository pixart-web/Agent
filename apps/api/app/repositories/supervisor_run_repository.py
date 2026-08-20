from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import SupervisorRunStatus


class SupervisorRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: SupervisorRun) -> None:
        self.session.add(run)

    def get_owned(self, run_id: UUID, user_id: UUID) -> SupervisorRun | None:
        statement = select(SupervisorRun).where(
            SupervisorRun.id == run_id,
            SupervisorRun.user_id == user_id,
        )
        return self.session.scalar(statement)

    def get_owned_for_update(self, run_id: UUID, user_id: UUID) -> SupervisorRun | None:
        statement = (
            select(SupervisorRun)
            .where(SupervisorRun.id == run_id, SupervisorRun.user_id == user_id)
            .with_for_update(of=SupervisorRun)
        )
        return self.session.scalar(statement)

    def has_active_for_command(self, command_id: UUID) -> bool:
        statement = select(SupervisorRun.id).where(
            SupervisorRun.command_id == command_id,
            SupervisorRun.status.in_([SupervisorRunStatus.PENDING, SupervisorRunStatus.RUNNING]),
        )
        return self.session.scalar(statement.limit(1)) is not None

    def list_for_command_owned(
        self,
        command_id: UUID,
        user_id: UUID,
    ) -> list[SupervisorRun]:
        statement = (
            select(SupervisorRun)
            .join(Command, Command.id == SupervisorRun.command_id)
            .where(
                SupervisorRun.command_id == command_id,
                Command.user_id == user_id,
            )
            .order_by(SupervisorRun.created_at.desc(), SupervisorRun.id)
        )
        return list(self.session.scalars(statement))
