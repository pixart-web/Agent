from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailRead,
    ConversationMessageCreate,
    ConversationRead,
    ConversationTurnRead,
)
from app.services.conversation_service import ConversationService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationTurnRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationTurnRead:
    try:
        return ConversationService(db).create(user.id, data.message)
    except WorkflowConflictError as error:
        raise_workflow_http_error(error)


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationRead]:
    return [
        ConversationRead.model_validate(item)
        for item in ConversationService(db).list(user.id, limit, offset)
    ]


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    conversation_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationDetailRead:
    try:
        return ConversationService(db).detail(conversation_id, user.id, limit, offset)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)


@router.post("/{conversation_id}/messages", response_model=ConversationTurnRead)
def create_message(
    conversation_id: UUID,
    data: ConversationMessageCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationTurnRead:
    try:
        return ConversationService(db).append(conversation_id, user.id, data.message)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
