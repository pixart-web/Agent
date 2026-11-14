from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.user import User
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
        user = self.session.get(User, user_id)
        if user is None or user.active_workspace_id is None:
            raise WorkflowConflictError("An active workspace is required")
        command = Command(
            user_id=user_id,
            workspace_id=user.active_workspace_id,
            input=data.input,
        )
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
        search: str | None,
        include_archived: bool,
    ) -> list[Command]:
        return self.commands.list_owned(
            user_id, limit, offset, command_status, search, include_archived
        )

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

    def archive(self, command_id: UUID, user_id: UUID) -> Command:
        command = self._locked(command_id, user_id)
        if command.status not in {
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
            CommandStatus.CANCELLED,
        }:
            self.session.rollback()
            raise WorkflowConflictError("Only terminal commands can be archived")
        command.archived_at = command.archived_at or utc_now()
        self.session.commit()
        self.session.refresh(command)
        return command

    def restore(self, command_id: UUID, user_id: UUID) -> Command:
        command = self._locked(command_id, user_id)
        command.archived_at = None
        self.session.commit()
        self.session.refresh(command)
        return command

    def duplicate(self, command_id: UUID, user_id: UUID) -> Command:
        source = self.get_owned(command_id, user_id)
        user = self.session.get(User, user_id)
        if user is None or user.active_workspace_id is None:
            raise WorkflowConflictError("An active workspace is required")
        duplicate = Command(
            user_id=user.id,
            workspace_id=user.active_workspace_id,
            input=source.input,
            duplicated_from_id=source.id,
        )
        self.commands.add(duplicate)
        self.session.commit()
        self.session.refresh(duplicate)
        return duplicate

    def _locked(self, command_id: UUID, user_id: UUID) -> Command:
        command = self.commands.get_owned_for_update(command_id, user_id)
        if command is None:
            self.session.rollback()
            raise WorkflowNotFoundError("Command not found")
        return command
