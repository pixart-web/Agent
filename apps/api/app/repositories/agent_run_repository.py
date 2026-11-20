from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.workflow_enums import AgentRunStatus
from app.workspaces.scope import active_workspace_id


class AgentRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: AgentRun) -> None:
        self.session.add(run)

    def get_owned_for_update(self, run_id: UUID, user_id: UUID) -> AgentRun | None:
        return self.session.scalar(
            self._owned(user_id).where(AgentRun.id == run_id).with_for_update(of=AgentRun)
        )

    def list_for_task_owned(self, task_id: UUID, user_id: UUID) -> list[AgentRun]:
        return list(
            self.session.scalars(
                self._owned(user_id)
                .where(AgentRun.task_id == task_id)
                .order_by(AgentRun.created_at.desc())
            )
        )

    def has_active(self, task_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(AgentRun.id).where(
                    AgentRun.task_id == task_id,
                    AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                )
            )
            is not None
        )

    def fail_stale_for_task(self, task_id: UUID, cutoff: datetime) -> int:
        """Mark runs still active since before `cutoff` as failed; returns how many."""
        stale = list(
            self.session.scalars(
                select(AgentRun)
                .where(
                    AgentRun.task_id == task_id,
                    AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                    AgentRun.created_at < cutoff,
                )
                .with_for_update()
            )
        )
        for run in stale:
            run.status = AgentRunStatus.FAILED
            run.error_code = "stale_run"
            run.error_message = "The agent did not finish in time. Run it again."
            run.completed_at = utc_now()
        return len(stale)

    def recent_for_agent(self, agent_id: str, user_id: UUID, limit: int = 20) -> list[AgentRun]:
        return list(
            self.session.scalars(
                self._owned(user_id)
                .where(AgentRun.agent_id == agent_id)
                .order_by(AgentRun.created_at.desc())
                .limit(limit)
            )
        )

    @staticmethod
    def _owned(user_id: UUID):
        return (
            select(AgentRun)
            .join(Task, Task.id == AgentRun.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Command.workspace_id == active_workspace_id(user_id))
        )
