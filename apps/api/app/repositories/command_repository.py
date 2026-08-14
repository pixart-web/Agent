from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.workflow_enums import CommandStatus


class CommandRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, command: Command) -> None:
        self.session.add(command)

    def get_owned(self, command_id: UUID, user_id: UUID) -> Command | None:
        statement = select(Command).where(
            Command.id == command_id,
            Command.user_id == user_id,
        )
        return self.session.scalar(statement)

    def get_owned_for_update(self, command_id: UUID, user_id: UUID) -> Command | None:
        statement = (
            select(Command)
            .where(
                Command.id == command_id,
                Command.user_id == user_id,
            )
            .with_for_update(of=Command)
        )
        return self.session.scalar(statement)

    def list_owned(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        command_status: CommandStatus | None,
    ) -> list[Command]:
        statement = (
            select(Command)
            .where(Command.user_id == user_id)
            .order_by(Command.created_at.desc(), Command.id)
            .limit(limit)
            .offset(offset)
        )
        if command_status is not None:
            statement = statement.where(Command.status == command_status)
        return list(self.session.scalars(statement))
