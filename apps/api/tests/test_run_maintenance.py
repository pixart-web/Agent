from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.audit_log import AuditLog
from app.models.command import Command
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import AgentRunStatus, CommandStatus, SupervisorRunStatus
from app.services.run_maintenance import fail_abandoned_runs
from tests.test_specialized_agents import ready_task
from tests.test_supervisor import register_and_create_command, seed_agents


def test_abandoned_planning_run_is_failed_and_frees_the_command(
    client: TestClient, db_session: Session
) -> None:
    seed_agents(db_session)
    _headers, command = register_and_create_command(client, email="abandoned-plan@example.com")
    row = db_session.get(Command, UUID(command["id"]))
    row.status = CommandStatus.PLANNING
    fresh = SupervisorRun(
        command_id=row.id,
        user_id=row.user_id,
        status=SupervisorRunStatus.RUNNING,
        provider="ollama",
        model="gemma4",
        prompt_version="v1",
        correlation_id=row.id,
    )
    old = SupervisorRun(
        command_id=row.id,
        user_id=row.user_id,
        status=SupervisorRunStatus.RUNNING,
        provider="ollama",
        model="gemma4",
        prompt_version="v1",
        correlation_id=row.id,
        created_at=utc_now() - timedelta(hours=3),
    )
    db_session.add_all([fresh, old])
    db_session.commit()

    result = fail_abandoned_runs(db_session)

    assert result == {"supervisor_runs": 1, "agent_runs": 0}
    db_session.expire_all()
    assert db_session.get(SupervisorRun, old.id).status == SupervisorRunStatus.FAILED
    assert db_session.get(SupervisorRun, old.id).error_code == "stale_run"
    assert db_session.get(SupervisorRun, fresh.id).status == SupervisorRunStatus.RUNNING
    assert db_session.get(Command, row.id).status == CommandStatus.PENDING
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "supervisor_run_abandoned")
    )


def test_abandoned_agent_run_is_failed(client: TestClient, db_session: Session) -> None:
    _headers, command, task = ready_task(
        client, db_session, "support", "abandoned-agent@example.com"
    )
    run = AgentRun(
        task_id=UUID(task["id"]),
        agent_id="support",
        user_id=UUID(command["user_id"]) if "user_id" in command else None,
        status=AgentRunStatus.RUNNING,
        provider="ollama",
        model="gemma4",
        prompt_version="support-v1",
        correlation_id=UUID(command["id"]),
        created_at=utc_now() - timedelta(hours=5),
    )
    if run.user_id is None:
        from app.models.user import User

        run.user_id = db_session.scalar(
            select(User.id).where(User.email == "abandoned-agent@example.com")
        )
    db_session.add(run)
    db_session.commit()

    assert fail_abandoned_runs(db_session) == {"supervisor_runs": 0, "agent_runs": 1}
    db_session.expire_all()
    assert db_session.get(AgentRun, run.id).status == AgentRunStatus.FAILED
    # A second pass finds nothing more to do.
    assert fail_abandoned_runs(db_session) == {"supervisor_runs": 0, "agent_runs": 0}
