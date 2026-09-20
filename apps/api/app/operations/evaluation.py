from datetime import timedelta
from decimal import Decimal
from math import ceil

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.supervisor_run import SupervisorRun
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import (
    AgentRunStatus,
    SupervisorRunStatus,
    TaskExecutionStatus,
    TaskStatus,
)


class ServiceEvaluation(BaseModel):
    total: int
    successful: int
    success_rate: float | None
    p95_latency_ms: int | None


class ProductionEvaluation(BaseModel):
    window_days: int
    generated_at: str
    supervisor: ServiceEvaluation
    agents: ServiceEvaluation
    executions: ServiceEvaluation
    tasks: ServiceEvaluation
    supervisor_cost_by_currency: dict[str, Decimal]
    sufficient_sample: bool


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * 0.95) - 1)]


def _evaluation(total: int, successful: int, latencies: list[int]) -> ServiceEvaluation:
    return ServiceEvaluation(
        total=total,
        successful=successful,
        success_rate=successful / total if total else None,
        p95_latency_ms=_p95(latencies),
    )


def evaluate_production(session: Session, *, window_days: int = 30) -> ProductionEvaluation:
    now = utc_now()
    since = now - timedelta(days=window_days)

    supervisor_statuses = list(
        session.execute(
            select(SupervisorRun.status, SupervisorRun.latency_ms).where(
                SupervisorRun.created_at >= since,
                SupervisorRun.status.in_(
                    (SupervisorRunStatus.COMPLETED, SupervisorRunStatus.FAILED)
                ),
            )
        )
    )
    agent_statuses = list(
        session.execute(
            select(AgentRun.status, AgentRun.latency_ms).where(
                AgentRun.created_at >= since,
                AgentRun.status.in_((AgentRunStatus.COMPLETED, AgentRunStatus.FAILED)),
            )
        )
    )
    execution_statuses = list(
        session.execute(
            select(TaskExecution.status, TaskExecution.duration_ms).where(
                TaskExecution.created_at >= since,
                TaskExecution.status.in_(
                    (TaskExecutionStatus.SUCCEEDED, TaskExecutionStatus.FAILED)
                ),
            )
        )
    )
    task_statuses = list(
        session.scalars(
            select(Task.status).where(
                Task.created_at >= since,
                Task.status.in_((TaskStatus.COMPLETED, TaskStatus.FAILED)),
            )
        )
    )
    costs = {
        currency: Decimal(total or 0)
        for currency, total in session.execute(
            select(SupervisorRun.currency, func.sum(SupervisorRun.estimated_cost))
            .where(
                SupervisorRun.created_at >= since,
                SupervisorRun.estimated_cost.is_not(None),
                SupervisorRun.currency.is_not(None),
            )
            .group_by(SupervisorRun.currency)
        )
    }

    return ProductionEvaluation(
        window_days=window_days,
        generated_at=now.isoformat(),
        supervisor=_evaluation(
            len(supervisor_statuses),
            sum(status == SupervisorRunStatus.COMPLETED for status, _ in supervisor_statuses),
            [latency for _, latency in supervisor_statuses if latency is not None],
        ),
        agents=_evaluation(
            len(agent_statuses),
            sum(status == AgentRunStatus.COMPLETED for status, _ in agent_statuses),
            [latency for _, latency in agent_statuses if latency is not None],
        ),
        executions=_evaluation(
            len(execution_statuses),
            sum(status == TaskExecutionStatus.SUCCEEDED for status, _ in execution_statuses),
            [latency for _, latency in execution_statuses if latency is not None],
        ),
        tasks=_evaluation(
            len(task_statuses),
            sum(status == TaskStatus.COMPLETED for status in task_statuses),
            [],
        ),
        supervisor_cost_by_currency=costs,
        sufficient_sample=all(
            count >= 20
            for count in (
                len(supervisor_statuses),
                len(agent_statuses),
                len(execution_statuses),
                len(task_statuses),
            )
        ),
    )
