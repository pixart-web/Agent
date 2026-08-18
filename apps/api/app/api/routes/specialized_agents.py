from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.exceptions import AgentNotRegisteredError, AgentProposalError
from app.agents.runner import AgentRunnerResult, AgentRunnerService
from app.ai.base import LLMProvider
from app.ai.provider_factory import get_llm_provider
from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.execution import TaskActionRead
from app.schemas.specialized_agent import (
    AgentCapabilitiesRead,
    AgentOverviewRead,
    AgentReassignmentRequest,
    AgentRunRead,
    AgentRunRequest,
    AgentRunResponse,
)
from app.schemas.task import TaskRead
from app.services.agent_management_service import AgentManagementService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["specialized-agents"])


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
    return AgentOverviewRead.model_validate(value)


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
