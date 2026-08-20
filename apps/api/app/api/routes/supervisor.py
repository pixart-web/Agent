from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.ai.base import LLMProvider
from app.ai.provider_factory import get_llm_provider
from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.plan import PlanRead
from app.schemas.supervisor import (
    RegeneratePlanRequest,
    SupervisorPlanResponse,
    SupervisorRunRead,
)
from app.schemas.task import TaskRead
from app.services.supervisor_run_service import SupervisorRunService
from app.services.supervisor_service import SupervisorPlanningResult, SupervisorService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(prefix="/commands", tags=["supervisor"])


def _planning_response(result: SupervisorPlanningResult) -> SupervisorPlanResponse:
    return SupervisorPlanResponse(
        plan=PlanRead.model_validate(result.plan),
        tasks=[TaskRead.model_validate(task) for task in result.tasks],
        run=SupervisorRunRead.model_validate(result.run),
    )


@router.post(
    "/{command_id}/generate-plan",
    response_model=SupervisorPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> SupervisorPlanResponse:
    try:
        result = SupervisorService(db, provider).generate(command_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return _planning_response(result)


@router.post(
    "/{command_id}/regenerate-plan",
    response_model=SupervisorPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_plan(
    command_id: UUID,
    data: RegeneratePlanRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> SupervisorPlanResponse:
    try:
        result = SupervisorService(db, provider).regenerate(
            command_id,
            user.id,
            data.feedback,
        )
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return _planning_response(result)


@router.get("/{command_id}/supervisor-runs", response_model=list[SupervisorRunRead])
def list_supervisor_runs(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SupervisorRunRead]:
    try:
        runs = SupervisorRunService(db).list_for_command(command_id, user.id)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return [SupervisorRunRead.model_validate(run) for run in runs]
