"""Background Supervisor planning (Celery worker side).

The API opens the run (`SupervisorService.start`) and enqueues `complete_supervisor_run`;
the worker calls the local model and stores the plan, or marks the run failed. The web and
desktop clients follow the run through `GET /commands/{id}/supervisor-runs`.
"""

import logging
from uuid import UUID

from app.ai.base import LLMProvider
from app.ai.exceptions import AIError, SupervisorPlanningError
from app.ai.provider_factory import get_llm_provider
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.services.supervisor_service import PlanningContext, SupervisorService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

logger = logging.getLogger(__name__)


class _UnavailableProvider:
    """Stands in when the worker cannot build the provider, so the run is marked failed
    through the normal path with the configuration error as its reason."""

    provider_name = "unavailable"
    model_name = "unavailable"

    def __init__(self, error: AIError) -> None:
        self.error = error

    def generate_structured(self, **_kwargs: object) -> object:
        raise self.error


def run_supervisor_payload(payload: dict[str, object]) -> None:
    context = PlanningContext.from_payload(payload)
    command_id = UUID(str(payload["command_id"]))
    user_id = UUID(str(payload["user_id"]))
    provider: LLMProvider
    try:
        provider = get_llm_provider()
    except AIError as error:
        provider = _UnavailableProvider(error)  # type: ignore[assignment]
    with SessionLocal() as session:
        try:
            SupervisorService(session, provider).complete(context, command_id, user_id)
        except (AIError, SupervisorPlanningError, WorkflowConflictError, WorkflowNotFoundError):
            # The service has already recorded the failure on the run.
            logger.info("supervisor_background_run_failed", extra={"run_id": str(context.run_id)})


@celery_app.task(name="app.services.supervisor_tasks.complete_supervisor_run")
def complete_supervisor_run(payload: dict[str, object]) -> None:
    run_supervisor_payload(payload)
