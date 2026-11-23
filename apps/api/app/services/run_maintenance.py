"""Marks AI runs abandoned by a dead worker or API as failed, without waiting for a new start.

A Supervisor or agent run that is still `pending`/`running` after the longest possible model
work (see the services' `stale_cutoff`) can no longer finish. Left alone it keeps the page
showing "working…" until somebody starts another run. The automation scheduler calls
`fail_abandoned_runs` on every pass.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.command import Command
from app.models.plan import Plan
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import (
    ActorType,
    AgentRunStatus,
    CommandStatus,
    SupervisorRunStatus,
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Same margins as SupervisorService / AgentRunnerService.stale_cutoff.
MARGIN_SECONDS = 120
SUPERVISOR_MODEL_CALLS = 1
AGENT_MODEL_CALLS = 3


def _cutoff(settings: Settings, model_calls: int, now: datetime) -> datetime:
    budget = model_calls * settings.ai_request_timeout_seconds * (settings.ai_max_retries + 1)
    return now - timedelta(seconds=budget + MARGIN_SECONDS)


def fail_abandoned_runs(
    session: Session, settings: Settings | None = None, now: datetime | None = None
) -> dict[str, int]:
    settings = settings or get_settings()
    now = now or utc_now()
    audit = AuditService(session)
    supervisor_runs = list(
        session.scalars(
            select(SupervisorRun)
            .where(
                SupervisorRun.status.in_(
                    [SupervisorRunStatus.PENDING, SupervisorRunStatus.RUNNING]
                ),
                SupervisorRun.created_at < _cutoff(settings, SUPERVISOR_MODEL_CALLS, now),
            )
            .with_for_update(skip_locked=True)
        )
    )
    for run in supervisor_runs:
        run.status = SupervisorRunStatus.FAILED
        run.error_code = "stale_run"
        run.error_message = "Planning did not finish in time. Start it again."
        run.completed_at = now
        command = session.get(Command, run.command_id)
        has_plan = session.scalar(
            select(Plan.id).where(Plan.command_id == run.command_id, Plan.is_current).limit(1)
        )
        if command is not None and command.status == CommandStatus.PLANNING and not has_plan:
            command.status = CommandStatus.PENDING
        audit.record(
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            event_type="supervisor_run_abandoned",
            resource_type="supervisor_run",
            resource_id=run.id,
            metadata={"command_id": str(run.command_id)},
            correlation_id=run.correlation_id,
        )
    agent_runs = list(
        session.scalars(
            select(AgentRun)
            .where(
                AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                AgentRun.created_at < _cutoff(settings, AGENT_MODEL_CALLS, now),
            )
            .with_for_update(skip_locked=True)
        )
    )
    for run in agent_runs:
        run.status = AgentRunStatus.FAILED
        run.error_code = "stale_run"
        run.error_message = "The agent did not finish in time. Run it again."
        run.completed_at = now
        audit.record(
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            event_type="agent_run_abandoned",
            resource_type="agent_run",
            resource_id=run.id,
            metadata={"task_id": str(run.task_id), "agent_id": run.agent_id},
            correlation_id=run.correlation_id,
        )
    session.commit()
    result = {"supervisor_runs": len(supervisor_runs), "agent_runs": len(agent_runs)}
    if supervisor_runs or agent_runs:
        logger.info("abandoned_runs_failed", extra=result)
    return result
