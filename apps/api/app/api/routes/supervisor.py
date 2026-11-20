from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.base import LLMProvider
from app.ai.exceptions import AIProviderUnavailableError
from app.ai.provider_factory import get_llm_provider
from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.supervisor_run import SupervisorRun
from app.models.user import User
from app.schemas.plan import PlanRead
from app.schemas.supervisor import (
    RegeneratePlanRequest,
    SupervisorPlanResponse,
    SupervisorRunRead,
    SupervisorRunStart,
)
from app.schemas.task import TaskRead
from app.services.supervisor_run_service import SupervisorRunService
from app.services.supervisor_service import SupervisorPlanningResult, SupervisorService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(prefix="/commands", tags=["supervisor"])

Enqueue = Callable[[dict[str, object]], None]


def enqueue_supervisor_run(payload: dict[str, object]) -> None:
    from app.services.supervisor_tasks import complete_supervisor_run  # noqa: PLC0415

    complete_supervisor_run.delay(payload)


def get_supervisor_enqueue() -> Enqueue:
    return enqueue_supervisor_run


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


@router.post(
    "/{command_id}/supervisor-runs",
    response_model=SupervisorRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_supervisor_run(
    command_id: UUID,
    data: SupervisorRunStart,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    enqueue: Annotated[Enqueue, Depends(get_supervisor_enqueue)],
) -> SupervisorRunRead:
    """Plan in the background: answers at once with the running run, which clients follow
    through `GET /commands/{id}/supervisor-runs`. With feedback, revises the draft plan."""
    service = SupervisorService(db, provider)
    try:
        context = service.start(command_id, user.id, data.feedback)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    payload = {**context.to_payload(), "command_id": str(command_id), "user_id": str(user.id)}
    try:
        enqueue(payload)
    except Exception as error:
        service.fail(
            context.run_id,
            command_id,
            user.id,
            AIProviderUnavailableError("Background planning is unavailable"),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background planning is unavailable. Try again in a moment.",
        ) from error
    run = db.get(SupervisorRun, context.run_id)
    db.refresh(run)
    return SupervisorRunRead.model_validate(run)


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
