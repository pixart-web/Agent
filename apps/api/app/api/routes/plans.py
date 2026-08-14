from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanRead
from app.services.plan_service import PlanService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["plans"])


@router.post(
    "/commands/{command_id}/plan",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    command_id: UUID,
    data: PlanCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanRead:
    try:
        plan = PlanService(db).create(command_id, user.id, data)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return PlanRead.model_validate(plan)


@router.get("/commands/{command_id}/plan", response_model=PlanRead)
def get_plan(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanRead:
    try:
        plan = PlanService(db).get_for_command_owned(command_id, user.id)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return PlanRead.model_validate(plan)
