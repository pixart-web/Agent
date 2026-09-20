from uuid import UUID

from sqlalchemy import select

from app.ai.exceptions import AIError
from app.ai.provider_factory import get_llm_provider
from app.automations.service import AutomationService
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.models.plan import Plan
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import SupervisorRunStatus
from app.services.supervisor_service import SupervisorService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


@celery_app.task(name="app.automations.tasks.plan_automation_command")
def plan_automation_command(command_id: str, user_id: str, run_id: str) -> None:
    command_uuid = UUID(command_id)
    user_uuid = UUID(user_id)
    run_uuid = UUID(run_id)
    try:
        with SessionLocal() as session:
            SupervisorService(session, get_llm_provider()).generate(command_uuid, user_uuid)
    except WorkflowConflictError:
        with SessionLocal() as session:
            plan_exists = session.scalar(
                select(Plan.id).where(
                    Plan.command_id == command_uuid,
                    Plan.is_current.is_(True),
                )
            )
        if plan_exists is None:
            with SessionLocal() as session:
                active_run = session.scalar(
                    select(SupervisorRun.id).where(
                        SupervisorRun.command_id == command_uuid,
                        SupervisorRun.status == SupervisorRunStatus.RUNNING,
                    )
                )
            if active_run is None:
                AutomationService().fail_planning_run(
                    user_uuid,
                    run_uuid,
                    error_code="planning_conflict",
                    error_message="Supervisor could not plan the automation command",
                )
            # Otherwise another duplicate delivery is still planning this command.
            return
    except WorkflowNotFoundError:
        AutomationService().fail_planning_run(
            user_uuid,
            run_uuid,
            error_code="command_not_found",
            error_message="Automation command is no longer available",
        )
        return
    except AIError as error:
        AutomationService().fail_planning_run(
            user_uuid,
            run_uuid,
            error_code=type(error).__name__,
            error_message="Supervisor planning failed safely",
        )
        raise
    AutomationService().complete_planning_run(user_uuid, run_uuid)
