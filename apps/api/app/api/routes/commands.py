from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.models.workflow_enums import CommandStatus
from app.schemas.command import CommandCreate, CommandRead
from app.services.command_service import CommandService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("", response_model=CommandRead, status_code=status.HTTP_201_CREATED)
def create_command(
    data: CommandCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommandRead:
    return CommandRead.model_validate(CommandService(db).create(user.id, data))


@router.get("", response_model=list[CommandRead])
def list_commands(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    command_status: Annotated[CommandStatus | None, Query(alias="status")] = None,
) -> list[CommandRead]:
    commands = CommandService(db).list_owned(
        user.id,
        limit,
        offset,
        command_status,
    )
    return [CommandRead.model_validate(command) for command in commands]


@router.get("/{command_id}", response_model=CommandRead)
def get_command(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommandRead:
    try:
        command = CommandService(db).get_owned(command_id, user.id)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return CommandRead.model_validate(command)


@router.post("/{command_id}/cancel", response_model=CommandRead)
def cancel_command(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommandRead:
    try:
        command = CommandService(db).cancel(command_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return CommandRead.model_validate(command)
