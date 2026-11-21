"""Background Supervisor planning (Celery worker side).

The API opens the run (`SupervisorService.start`) and enqueues `complete_supervisor_run`;
the worker calls the local model and stores the plan, or marks the run failed. The web and
desktop clients follow the run through `GET /commands/{id}/supervisor-runs`.
"""

import logging
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.ai.base import LLMProvider
from app.ai.exceptions import AIError, AIProviderTimeoutError, SupervisorPlanningError
from app.ai.provider_factory import get_llm_provider
from app.core.config import get_settings
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


class TimeBoundProvider:
    """Turns the worker's soft time limit into a normal AI timeout, so the run is marked
    failed with a clear reason instead of a generic error."""

    def __init__(self, inner: LLMProvider) -> None:
        self.inner = inner

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)

    def generate_structured(self, **kwargs: object) -> object:
        try:
            return self.inner.generate_structured(**kwargs)
        except SoftTimeLimitExceeded as error:
            raise AIProviderTimeoutError(
                "The local AI did not finish within the time limit"
            ) from error


def model_budget_seconds(model_calls: int) -> int:
    """Longest time the local model may take for `model_calls` calls, retries included."""
    settings = get_settings()
    return model_calls * settings.ai_request_timeout_seconds * (settings.ai_max_retries + 1)


def worker_provider() -> LLMProvider:
    try:
        return TimeBoundProvider(get_llm_provider())  # type: ignore[return-value]
    except AIError as error:
        return _UnavailableProvider(error)  # type: ignore[return-value]


def run_supervisor_payload(payload: dict[str, object]) -> None:
    context = PlanningContext.from_payload(payload)
    command_id = UUID(str(payload["command_id"]))
    user_id = UUID(str(payload["user_id"]))
    provider = worker_provider()
    with SessionLocal() as session:
        try:
            SupervisorService(session, provider).complete(context, command_id, user_id)
        except (AIError, SupervisorPlanningError, WorkflowConflictError, WorkflowNotFoundError):
            # The service has already recorded the failure on the run.
            logger.info("supervisor_background_run_failed", extra={"run_id": str(context.run_id)})


@celery_app.task(
    name="app.services.supervisor_tasks.complete_supervisor_run",
    soft_time_limit=model_budget_seconds(1) + 60,
    time_limit=model_budget_seconds(1) + 90,
)
def complete_supervisor_run(payload: dict[str, object]) -> None:
    run_supervisor_payload(payload)
