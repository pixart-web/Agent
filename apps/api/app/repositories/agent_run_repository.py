from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.workflow_enums import AgentRunStatus


class AgentRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: AgentRun) -> None:
        self.session.add(run)

    def get_owned_for_update(self, run_id: UUID, user_id: UUID) -> AgentRun | None:
        return self.session.scalar(
            select(AgentRun)
            .where(AgentRun.id == run_id, AgentRun.user_id == user_id)
            .with_for_update(of=AgentRun)
        )

    def list_for_task_owned(self, task_id: UUID, user_id: UUID) -> list[AgentRun]:
        return list(
            self.session.scalars(
                select(AgentRun)
                .where(AgentRun.task_id == task_id, AgentRun.user_id == user_id)
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

    def recent_for_agent(self, agent_id: str, user_id: UUID, limit: int = 20) -> list[AgentRun]:
        return list(
            self.session.scalars(
                select(AgentRun)
                .where(AgentRun.agent_id == agent_id, AgentRun.user_id == user_id)
                .order_by(AgentRun.created_at.desc())
                .limit(limit)
            )
        )
