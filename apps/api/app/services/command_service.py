from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.workflow_enums import CommandStatus
from app.repositories.command_repository import CommandRepository
from app.schemas.command import CommandCreate
from app.services.execution_cancellation_service import ExecutionCancellationService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class CommandService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.commands = CommandRepository(session)
        self.execution_cancellation = ExecutionCancellationService(session)

    def create(self, user_id: UUID, data: CommandCreate) -> Command:
        command = Command(user_id=user_id, input=data.input)
        self.commands.add(command)
        self.session.commit()
        self.session.refresh(command)
        return command

    def list_owned(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        command_status: CommandStatus | None,
    ) -> list[Command]:
        return self.commands.list_owned(user_id, limit, offset, command_status)

    def get_owned(self, command_id: UUID, user_id: UUID) -> Command:
        command = self.commands.get_owned(command_id, user_id)
        if command is None:
            raise WorkflowNotFoundError("Command not found")
        return command

    def cancel(self, command_id: UUID, user_id: UUID) -> Command:
        try:
            command = self.commands.get_owned_for_update(command_id, user_id)
            if command is None:
                raise WorkflowNotFoundError("Command not found")
            if command.status in {CommandStatus.COMPLETED, CommandStatus.CANCELLED}:
                raise WorkflowConflictError("Command cannot be cancelled from its current state")
            command.status = CommandStatus.CANCELLED
            command.completed_at = utc_now()
            self.execution_cancellation.cancel_for_command(command.id, user_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(command)
        return command
