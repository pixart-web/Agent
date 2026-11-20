from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.exceptions import AgentNotRegisteredError, AgentProposalError
from app.agents.runner import AgentRunnerResult, AgentRunnerService, context_to_payload
from app.ai.base import LLMProvider
from app.ai.exceptions import AIProviderUnavailableError
from app.ai.provider_factory import build_local_provider, get_llm_provider
from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.agent_run import AgentRun
from app.models.user import User
from app.schemas.execution import TaskActionRead
from app.schemas.specialized_agent import (
    AgentCapabilitiesRead,
    AgentConfigurationRead,
    AgentConfigurationUpdate,
    AgentOverviewRead,
    AgentReassignmentRequest,
    AgentRunRead,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStart,
)
from app.schemas.task import TaskRead
from app.services.agent_management_service import AgentManagementService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["specialized-agents"])

Enqueue = Callable[[dict[str, object]], None]


def enqueue_agent_run(payload: dict[str, object]) -> None:
    from app.services.agent_run_tasks import complete_agent_run  # noqa: PLC0415

    complete_agent_run.delay(payload)


def get_agent_enqueue() -> Enqueue:
    return enqueue_agent_run


def _raise(error: Exception) -> None:
    if isinstance(error, AgentNotRegisteredError):
        error = WorkflowNotFoundError(str(error))
    if isinstance(error, AgentProposalError):
        error = WorkflowConflictError(str(error))
    raise_workflow_http_error(error)


def _response(result: AgentRunnerResult) -> AgentRunResponse:
    return AgentRunResponse(
        run=AgentRunRead.model_validate(result.run),
        actions=[TaskActionRead.model_validate(action) for action in result.actions],
    )


@router.post("/tasks/{task_id}/run-agent", response_model=AgentRunResponse, status_code=201)
def run_agent(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> AgentRunResponse:
    try:
        return _response(AgentRunnerService(db, provider).run(task_id, user.id))
    except Exception as error:
        _raise(error)


@router.post("/tasks/{task_id}/rerun-agent", response_model=AgentRunResponse, status_code=201)
def rerun_agent(
    task_id: UUID,
    data: AgentRunRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> AgentRunResponse:
    try:
        return _response(AgentRunnerService(db, provider).rerun(task_id, user.id, data.feedback))
    except Exception as error:
        _raise(error)


@router.post(
    "/tasks/{task_id}/agent-runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_agent_run(
    task_id: UUID,
    data: AgentRunStart,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    enqueue: Annotated[Enqueue, Depends(get_agent_enqueue)],
) -> AgentRunRead:
    """Run the task's agent in the background: answers at once with the running run, which
    clients follow through `GET /tasks/{id}/agent-runs`."""
    service = AgentRunnerService(db, provider)
    try:
        context, run_id = service.start(task_id, user.id, data.feedback)
    except Exception as error:
        _raise(error)
    payload = {
        "context": context_to_payload(context),
        "run_id": str(run_id),
        "user_id": str(user.id),
    }
    try:
        enqueue(payload)
    except Exception as error:
        service.fail(
            run_id, user.id, AIProviderUnavailableError("Background agent runs are unavailable")
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background agent runs are unavailable. Try again in a moment.",
        ) from error
    run = db.get(AgentRun, run_id)
    db.refresh(run)
    return AgentRunRead.model_validate(run)


@router.get("/tasks/{task_id}/agent-runs", response_model=list[AgentRunRead])
def list_agent_runs(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AgentRunRead]:
    try:
        runs = AgentManagementService(db).list_runs(task_id, user.id)
    except Exception as error:
        _raise(error)
    return [AgentRunRead.model_validate(run) for run in runs]


@router.get("/agents/{agent_id}/capabilities", response_model=AgentCapabilitiesRead)
def capabilities(
    agent_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentCapabilitiesRead:
    try:
        value = AgentManagementService(db).capabilities(
            agent_id, settings.agent_max_actions_per_task
        )
    except Exception as error:
        _raise(error)
    return AgentCapabilitiesRead.model_validate(value)


@router.get("/agents/{agent_id}/overview", response_model=AgentOverviewRead)
def overview(
    agent_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentOverviewRead:
    try:
        value = AgentManagementService(db).overview(
            agent_id, user.id, settings.agent_max_actions_per_task
        )
    except Exception as error:
        _raise(error)
    if value["operational_status"] != "disabled":
        if settings.ai_provider == "fake":
            value["operational_status"] = "sandbox"
            value["operational_message"] = "Sandbox provider configured"
        else:
            health = build_local_provider(settings).health()
            if health["reachable"] and health["model_installed"]:
                value["operational_status"] = "operational"
                value["operational_message"] = f"Local model {settings.ai_local_model} ready"
            else:
                value["operational_status"] = "unavailable"
                value["operational_message"] = (
                    f"Local model {settings.ai_local_model} is not installed"
                    if health["reachable"]
                    else "Local AI runtime is not reachable"
                )
    return AgentOverviewRead.model_validate(value)


@router.get("/agents/{agent_id}/configuration", response_model=AgentConfigurationRead)
def get_configuration(
    agent_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentConfigurationRead:
    try:
        value = AgentManagementService(db).configuration(
            agent_id, user.id, settings.agent_max_actions_per_task
        )
    except Exception as error:
        _raise(error)
    return AgentConfigurationRead.model_validate(value)


@router.patch("/agents/{agent_id}/configuration", response_model=AgentConfigurationRead)
def update_configuration(
    agent_id: str,
    data: AgentConfigurationUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentConfigurationRead:
    try:
        value = AgentManagementService(db).update_configuration(
            agent_id, user.id, settings.agent_max_actions_per_task, data
        )
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except Exception as error:
        _raise(error)
    return AgentConfigurationRead.model_validate(value)


@router.post("/tasks/{task_id}/reassign-agent", response_model=TaskRead)
def reassign_agent(
    task_id: UUID,
    data: AgentReassignmentRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskRead:
    try:
        task = AgentManagementService(db).reassign(task_id, user.id, data.agent_id)
    except Exception as error:
        _raise(error)
    return TaskRead.model_validate(task)
