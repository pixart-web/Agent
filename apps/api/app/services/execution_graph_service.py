"""Execution graph of a plan: tasks as nodes placed in dependency levels, and each task's
step log (status changes, agent runs and tool execution attempts) in time order."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.task_execution import TaskExecution
from app.models.task_status_history import TaskStatusHistory


@dataclass
class GraphStep:
    kind: str  # "status" | "agent_run" | "execution"
    at: datetime
    status: str
    title: str
    detail: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    note: str | None = None


@dataclass
class GraphNode:
    task: Task
    level: int
    depends_on: list[UUID]
    steps: list[GraphStep] = field(default_factory=list)


@dataclass
class ExecutionGraph:
    nodes: list[GraphNode]
    edges: list[tuple[UUID, UUID]]  # (depends_on_task_id, task_id)
    levels: int


def _levels(task_ids: list[UUID], parents: dict[UUID, list[UUID]]) -> dict[UUID, int]:
    """Longest-path level from the roots. Tasks caught in a cycle (which the dependency service
    refuses, but older data may hold) go one level after everything else."""
    level: dict[UUID, int] = {}
    pending = set(task_ids)
    while pending:
        progressed = False
        for task_id in list(pending):
            known = [parent for parent in parents.get(task_id, []) if parent in level]
            waiting = [p for p in parents.get(task_id, []) if p in pending and p != task_id]
            if waiting:
                continue
            level[task_id] = max((level[p] + 1 for p in known), default=0)
            pending.discard(task_id)
            progressed = True
        if not progressed:
            fallback = max(level.values(), default=-1) + 1
            for task_id in pending:
                level[task_id] = fallback
            break
    return level


def _status_step(item: TaskStatusHistory) -> GraphStep:
    return GraphStep(
        kind="status",
        at=item.created_at,
        status=str(item.to_status.value if hasattr(item.to_status, "value") else item.to_status),
        title="status",
        detail=(
            str(item.from_status.value if hasattr(item.from_status, "value") else item.from_status)
            if item.from_status is not None
            else None
        ),
        note=item.reason,
    )


def _run_step(run: AgentRun) -> GraphStep:
    status = run.status.value if hasattr(run.status, "value") else str(run.status)
    return GraphStep(
        kind="agent_run",
        at=run.created_at,
        status=status,
        title=run.agent_id,
        detail=run.proposal_summary,
        duration_ms=run.latency_ms,
        error_message=run.error_message,
    )


def _execution_step(execution: TaskExecution) -> GraphStep:
    status = execution.status.value if hasattr(execution.status, "value") else str(execution.status)
    return GraphStep(
        kind="execution",
        at=execution.started_at or execution.queued_at or execution.created_at,
        status=status,
        title=execution.tool_name,
        detail=f"#{execution.attempt_number}",
        duration_ms=execution.duration_ms,
        error_message=execution.error_message,
    )


class ExecutionGraphService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def for_plan(self, plan_id: UUID) -> ExecutionGraph:
        tasks = list(
            self.session.scalars(
                select(Task).where(Task.plan_id == plan_id).order_by(Task.sequence, Task.created_at)
            )
        )
        ids = [task.id for task in tasks]
        if not ids:
            return ExecutionGraph(nodes=[], edges=[], levels=0)

        known = set(ids)
        parents: dict[UUID, list[UUID]] = defaultdict(list)
        edges: list[tuple[UUID, UUID]] = []
        for dependency in self.session.scalars(
            select(TaskDependency).where(TaskDependency.task_id.in_(ids))
        ):
            if dependency.depends_on_task_id in known:
                parents[dependency.task_id].append(dependency.depends_on_task_id)
                edges.append((dependency.depends_on_task_id, dependency.task_id))

        steps: dict[UUID, list[GraphStep]] = defaultdict(list)
        for item in self.session.scalars(
            select(TaskStatusHistory).where(TaskStatusHistory.task_id.in_(ids))
        ):
            steps[item.task_id].append(_status_step(item))
        for run in self.session.scalars(select(AgentRun).where(AgentRun.task_id.in_(ids))):
            steps[run.task_id].append(_run_step(run))
        for execution in self.session.scalars(
            select(TaskExecution).where(TaskExecution.task_id.in_(ids))
        ):
            steps[execution.task_id].append(_execution_step(execution))

        level = _levels(ids, parents)
        nodes = [
            GraphNode(
                task=task,
                level=level[task.id],
                depends_on=parents.get(task.id, []),
                steps=sorted(steps.get(task.id, []), key=lambda step: step.at),
            )
            for task in tasks
        ]
        return ExecutionGraph(
            nodes=nodes,
            edges=edges,
            levels=max(level.values()) + 1,
        )
