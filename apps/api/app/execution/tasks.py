from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.execution.exceptions import ToolTimeoutError
from app.execution.policies import RetryPolicy
from app.execution.worker import ExecutionWorker


@celery_app.task(name="app.execution.tasks.execute_task_execution")
def execute_task_execution(execution_id: str) -> None:
    settings = get_settings()
    worker = ExecutionWorker(
        SessionLocal,
        retry_policy=RetryPolicy(system_max_retries=settings.execution_max_retries),
    )
    try:
        worker.execute(UUID(execution_id))
    except SoftTimeLimitExceeded as error:
        raise ToolTimeoutError("Tool execution exceeded its timeout") from error
