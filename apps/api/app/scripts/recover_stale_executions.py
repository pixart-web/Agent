from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import TaskActionStatus, TaskExecutionStatus


def main() -> None:
    settings = get_settings()
    cutoff = utc_now() - timedelta(seconds=settings.execution_stale_after_seconds)
    recovered = 0
    with SessionLocal() as session:
        executions = session.scalars(
            select(TaskExecution)
            .where(
                TaskExecution.status == TaskExecutionStatus.RUNNING,
                TaskExecution.started_at < cutoff,
            )
            .with_for_update(of=TaskExecution, skip_locked=True)
        )
        for execution in executions:
            execution.status = TaskExecutionStatus.FAILED
            execution.error_code = "stale_execution"
            execution.error_message = (
                "Worker heartbeat was lost; manual review is required before retry"
            )
            execution.completed_at = utc_now()
            action = session.get(TaskAction, execution.task_action_id)
            if action is not None and action.status == TaskActionStatus.RUNNING:
                action.status = TaskActionStatus.FAILED
            recovered += 1
        session.commit()
    print(f"Marked {recovered} stale execution(s) for manual review.")


if __name__ == "__main__":
    main()
