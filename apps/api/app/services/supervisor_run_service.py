from uuid import UUID

from sqlalchemy.orm import Session

from app.models.supervisor_run import SupervisorRun
from app.repositories.command_repository import CommandRepository
from app.repositories.supervisor_run_repository import SupervisorRunRepository
from app.services.workflow_errors import WorkflowNotFoundError


class SupervisorRunService:
    def __init__(self, session: Session) -> None:
        self.commands = CommandRepository(session)
        self.runs = SupervisorRunRepository(session)

    def list_for_command(self, command_id: UUID, user_id: UUID) -> list[SupervisorRun]:
        if self.commands.get_owned(command_id, user_id) is None:
            raise WorkflowNotFoundError("Command not found")
        return self.runs.list_for_command_owned(command_id, user_id)
