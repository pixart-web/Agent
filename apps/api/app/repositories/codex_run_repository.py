from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.codex_run import CodexRun
from app.models.workflow_enums import CodexRunStatus


class CodexRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: CodexRun) -> None:
        self.session.add(run)

    def get_for_action(self, action_id: UUID) -> CodexRun | None:
        return self.session.scalar(select(CodexRun).where(CodexRun.task_action_id == action_id))

    def get_for_action_for_update(self, action_id: UUID) -> CodexRun | None:
        return self.session.scalar(
            select(CodexRun)
            .where(CodexRun.task_action_id == action_id)
            .with_for_update(of=CodexRun)
        )

    def get_owned(self, run_id: UUID, user_id: UUID) -> CodexRun | None:
        return self.session.scalar(
            select(CodexRun).where(CodexRun.id == run_id, CodexRun.user_id == user_id)
        )

    def list_owned(
        self,
        user_id: UUID,
        *,
        status: CodexRunStatus | None,
        limit: int,
        offset: int,
    ) -> list[CodexRun]:
        statement = select(CodexRun).where(CodexRun.user_id == user_id)
        if status is not None:
            statement = statement.where(CodexRun.status == status)
        statement = (
            statement.order_by(CodexRun.created_at.desc(), CodexRun.id).limit(limit).offset(offset)
        )
        return list(self.session.scalars(statement))
