"""Background specialist agent runs (Celery worker side).

The API opens the run (`AgentRunnerService.start`) and enqueues `complete_agent_run`; the
worker calls the local model and stores the proposed actions, or marks the run failed. The
web and desktop clients follow the run through `GET /tasks/{id}/agent-runs`.
"""

import logging
from uuid import UUID

from app.agents.exceptions import AgentNotRegisteredError, AgentProposalError
from app.agents.runner import AgentRunnerService, context_from_payload
from app.ai.base import LLMProvider
from app.ai.exceptions import AIError
from app.ai.provider_factory import get_llm_provider
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.services.supervisor_tasks import _UnavailableProvider
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

logger = logging.getLogger(__name__)


def run_agent_payload(payload: dict[str, object]) -> None:
    context = context_from_payload(payload["context"])  # type: ignore[arg-type]
    run_id = UUID(str(payload["run_id"]))
    user_id = UUID(str(payload["user_id"]))
    provider: LLMProvider
    try:
        provider = get_llm_provider()
    except AIError as error:
        provider = _UnavailableProvider(error)  # type: ignore[assignment]
    with SessionLocal() as session:
        try:
            AgentRunnerService(session, provider).complete(context, run_id, user_id)
        except (
            AIError,
            AgentProposalError,
            AgentNotRegisteredError,
            WorkflowConflictError,
            WorkflowNotFoundError,
        ):
            # The runner has already recorded the failure (or cancellation) on the run.
            logger.info("agent_background_run_failed", extra={"agent_run_id": str(run_id)})


@celery_app.task(name="app.services.agent_run_tasks.complete_agent_run")
def complete_agent_run(payload: dict[str, object]) -> None:
    run_agent_payload(payload)
