from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import SupervisorRunStatus
from app.workspaces.scope import active_workspace_id


class SupervisorRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: SupervisorRun) -> None:
        self.session.add(run)

    def get_owned(self, run_id: UUID, user_id: UUID) -> SupervisorRun | None:
        statement = (
            select(SupervisorRun)
            .join(Command, Command.id == SupervisorRun.command_id)
            .where(
                SupervisorRun.id == run_id,
                Command.workspace_id == active_workspace_id(user_id),
            )
        )
        return self.session.scalar(statement)

    def get_owned_for_update(self, run_id: UUID, user_id: UUID) -> SupervisorRun | None:
        statement = (
            select(SupervisorRun)
            .join(Command, Command.id == SupervisorRun.command_id)
            .where(
                SupervisorRun.id == run_id,
                Command.workspace_id == active_workspace_id(user_id),
            )
            .with_for_update(of=SupervisorRun)
        )
        return self.session.scalar(statement)

    def fail_stale_for_command(self, command_id: UUID, cutoff: datetime) -> int:
        """Mark runs still active since before `cutoff` as failed; returns how many."""
        stale = list(
            self.session.scalars(
                select(SupervisorRun)
                .where(
                    SupervisorRun.command_id == command_id,
                    SupervisorRun.status.in_(
                        [SupervisorRunStatus.PENDING, SupervisorRunStatus.RUNNING]
                    ),
                    SupervisorRun.created_at < cutoff,
                )
                .with_for_update()
            )
        )
        for run in stale:
            run.status = SupervisorRunStatus.FAILED
            run.error_code = "stale_run"
            run.error_message = "Planning did not finish in time. Start it again."
            run.completed_at = utc_now()
        return len(stale)

    def has_active_for_command(self, command_id: UUID) -> bool:
        statement = select(SupervisorRun.id).where(
            SupervisorRun.command_id == command_id,
            SupervisorRun.status.in_([SupervisorRunStatus.PENDING, SupervisorRunStatus.RUNNING]),
        )
        return self.session.scalar(statement.limit(1)) is not None

    def list_for_command_owned(
        self,
        command_id: UUID,
        user_id: UUID,
    ) -> list[SupervisorRun]:
        statement = (
            select(SupervisorRun)
            .join(Command, Command.id == SupervisorRun.command_id)
            .where(
                SupervisorRun.command_id == command_id,
                Command.workspace_id == active_workspace_id(user_id),
            )
            .order_by(SupervisorRun.created_at.desc(), SupervisorRun.id)
        )
        return list(self.session.scalars(statement))
