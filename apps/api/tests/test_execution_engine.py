from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.execution.context_safety import sanitize_execution_payload
from app.execution.dispatcher import OutboxDispatcher
from app.execution.exceptions import (
    ToolInputValidationError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTransientError,
)
from app.execution.policies import RetryPolicy
from app.execution.registry import ToolDefinition, ToolRegistry
from app.execution.tools.internal import EchoInput, EchoOutput
from app.execution.tools.registry import build_tool_registry
from app.execution.worker import ExecutionWorker
from app.models.agent import Agent
from app.models.approval_request import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.command import Command
from app.models.outbox_event import OutboxEvent
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.user import User
from app.models.workflow_enums import (
    ApprovalStatus,
    CommandStatus,
    OutboxStatus,
    RiskLevel,
    TaskActionStatus,
    TaskExecutionStatus,
    TaskStatus,
)
from app.schemas.execution import TaskActionCreate
from app.services.execution_service import ExecutionService

PASSWORD = "securePassword123"


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Execution Owner"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_agents(db_session: Session) -> None:
    db_session.add_all(
        [
            Agent(id="marketing", name="Marketing", description="Campaign work"),
            Agent(id="supervisor", name="Supervisor", description="Coordination"),
            Agent(id="development", name="Development", description="Engineering"),
        ]
    )
    db_session.commit()


def setup_ready_tasks(
    client: TestClient,
    db_session: Session,
    *,
    task_count: int = 1,
    task_risk: str = "green",
    email: str = "execution@example.com",
) -> tuple[dict[str, str], dict[str, object], dict[str, object], list[dict[str, object]]]:
    seed_agents(db_session)
    headers = register(client, email)
    command_response = client.post(
        "/api/v1/commands",
        headers=headers,
        json={"input": "Run a safe internal workflow"},
    )
    assert command_response.status_code == 201
    command = command_response.json()
    plan_response = client.post(
        f"/api/v1/commands/{command['id']}/plan",
        headers=headers,
        json={"title": "Execution plan", "objective": "Prove the execution engine"},
    )
    assert plan_response.status_code == 201
    plan = plan_response.json()
    tasks = []
    for index in range(task_count):
        response = client.post(
            f"/api/v1/plans/{plan['id']}/tasks",
            headers=headers,
            json={
                "agent_id": "marketing",
                "title": f"Execution task {index + 1}",
                "instructions": "Execute the registered internal action.",
                "priority": "normal",
                "risk_level": task_risk,
                "sequence": index + 1,
            },
        )
        assert response.status_code == 201
        tasks.append(response.json())
    approval = client.post(f"/api/v1/plans/{plan['id']}/approve", headers=headers)
    assert approval.status_code == 200
    return headers, command, plan, tasks


def create_and_dispatch(
    client: TestClient,
    headers: dict[str, str],
    task_id: str,
    tool_name: str,
    payload: dict[str, object],
):
    action = client.post(
        f"/api/v1/tasks/{task_id}/actions",
        headers=headers,
        json={"tool_name": tool_name, "input_payload": payload},
    )
    assert action.status_code == 201
    dispatched = client.post(f"/api/v1/actions/{action.json()['id']}/dispatch", headers=headers)
    assert dispatched.status_code == 200
    return action.json(), dispatched.json()


@pytest.fixture
def session_factory(db_session: Session):
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def test_tool_registry_enforces_name_schema_agent_and_version() -> None:
    registry = build_tool_registry()
    echo = registry.get("internal.echo", "1")
    assert echo.risk_level == RiskLevel.GREEN
    assert registry.validate_input(echo, {"text": "hello"}, "marketing").text == "hello"

    with pytest.raises(ToolNotFoundError):
        registry.get("unknown.tool", "1")
    with pytest.raises(ToolInputValidationError):
        registry.validate_input(echo, {}, "marketing")
    with pytest.raises(ToolPermissionError):
        critical = registry.get("internal.simulate_critical_action", "1")
        registry.validate_input(critical, {"action": "test", "description": "test"}, "marketing")


def test_payload_sanitization_masks_nested_secrets() -> None:
    sanitized = sanitize_execution_payload(
        {
            "password": "do-not-store",
            "nested": {"api_key": "secret", "safe": "Bearer abc.def"},
            "items": [{"refresh-token": "value"}],
        }
    )
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "Bearer [REDACTED]"
    assert sanitized["items"][0]["refresh-token"] == "[REDACTED]"


def test_green_action_queues_executes_once_and_completes_workflow(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    headers, command, _plan, tasks = setup_ready_tasks(client, db_session)
    _action, dispatched = create_and_dispatch(
        client, headers, str(tasks[0]["id"]), "internal.echo", {"text": "Kiko"}
    )
    assert dispatched["approval"] is None
    assert dispatched["execution"]["status"] == "queued"

    worker = ExecutionWorker(
        session_factory,
        retry_policy=RetryPolicy(system_max_retries=3),
        worker_id="test-worker",
    )
    execution_id = UUID(dispatched["execution"]["id"])
    result = worker.execute(execution_id)
    assert result is not None and result.status == TaskExecutionStatus.SUCCEEDED
    assert worker.execute(execution_id) is None

    task = db_session.get(Task, UUID(tasks[0]["id"]))
    persisted_command = db_session.get(Command, UUID(command["id"]))
    assert task.status == TaskStatus.COMPLETED
    assert persisted_command.status == CommandStatus.COMPLETED
    assert db_session.scalar(select(AuditLog).where(AuditLog.event_type == "command_completed"))


def test_yellow_waits_for_approval_and_then_executes(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    action, dispatched = create_and_dispatch(
        client,
        headers,
        str(tasks[0]["id"]),
        "internal.simulate_external_action",
        {"action": "publish_post", "description": "Simulate publishing"},
    )
    assert dispatched["execution"] is None
    assert dispatched["approval"]["status"] == "pending"
    assert (
        db_session.scalar(
            select(TaskExecution).where(TaskExecution.task_action_id == UUID(action["id"]))
        )
        is None
    )

    approved = client.post(
        f"/api/v1/approvals/{dispatched['approval']['id']}/approve",
        headers=headers,
        json={"reason": "Approved simulation", "confirm_high_risk": False},
    )
    assert approved.status_code == 200
    execution_id = UUID(approved.json()["execution"]["id"])
    ExecutionWorker(session_factory, retry_policy=RetryPolicy(system_max_retries=3)).execute(
        execution_id
    )
    execution = db_session.get(TaskExecution, execution_id)
    assert execution.status == TaskExecutionStatus.SUCCEEDED
    assert execution.output_payload == {"simulated": True, "status": "success"}


def test_red_requires_reinforced_confirmation(client: TestClient, db_session: Session) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session, task_risk="red")
    action_response = client.post(
        f"/api/v1/tasks/{tasks[0]['id']}/actions",
        headers=headers,
        json={
            "tool_name": "internal.simulate_critical_action",
            "input_payload": {"action": "critical", "description": "Simulate critical"},
        },
    )
    assert action_response.status_code == 403

    task = db_session.get(Task, UUID(tasks[0]["id"]))
    task.agent_id = "development"
    db_session.commit()
    action, dispatched = create_and_dispatch(
        client,
        headers,
        str(tasks[0]["id"]),
        "internal.simulate_critical_action",
        {"action": "critical", "description": "Simulate critical"},
    )
    approval_id = dispatched["approval"]["id"]
    refused = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=headers,
        json={"confirm_high_risk": False},
    )
    assert refused.status_code == 409
    accepted = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=headers,
        json={"confirm_high_risk": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["action"]["id"] == action["id"]


def test_fingerprint_change_invalidates_approval(client: TestClient, db_session: Session) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    action, dispatched = create_and_dispatch(
        client,
        headers,
        str(tasks[0]["id"]),
        "internal.simulate_external_action",
        {"action": "publish_post", "description": "Original"},
    )
    stored = db_session.get(TaskAction, UUID(action["id"]))
    stored.input_payload = {"action": "publish_post", "description": "Changed"}
    db_session.commit()

    response = client.post(
        f"/api/v1/approvals/{dispatched['approval']['id']}/approve",
        headers=headers,
        json={"confirm_high_risk": False},
    )
    assert response.status_code == 409
    approval = db_session.get(ApprovalRequest, UUID(dispatched["approval"]["id"]))
    assert approval.status == ApprovalStatus.CANCELLED


class FlakyHandler:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, _context, payload: BaseModel) -> BaseModel:
        self.calls += 1
        if self.calls == 1:
            raise ToolTransientError("Temporary internal failure")
        return EchoOutput(text=EchoInput.model_validate(payload).text)


def flaky_registry(handler: FlakyHandler) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="internal.flaky",
            version="1",
            description="Test retry behavior.",
            agent_types=frozenset({"marketing"}),
            risk_level=RiskLevel.GREEN,
            timeout_seconds=10,
            max_retries=2,
            requires_approval=False,
            input_schema=EchoInput,
            output_schema=EchoOutput,
            handler=handler,
        )
    )
    return registry


def test_retry_preserves_attempts_and_later_succeeds(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    _headers, command, _plan, tasks = setup_ready_tasks(client, db_session)
    user = db_session.scalar(select(User).where(User.email == "execution@example.com"))
    handler = FlakyHandler()
    registry = flaky_registry(handler)
    service = ExecutionService(db_session, registry)
    action = service.create_action(
        UUID(tasks[0]["id"]),
        user.id,
        TaskActionCreate(tool_name="internal.flaky", input_payload={"text": "retry"}),
    )
    dispatched = service.dispatch(action.id, user.id)
    worker = ExecutionWorker(
        session_factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
    )
    first = worker.execute(dispatched.execution.id)
    assert first.status == TaskExecutionStatus.FAILED
    attempts = list(
        db_session.scalars(
            select(TaskExecution)
            .where(TaskExecution.task_action_id == action.id)
            .order_by(TaskExecution.attempt_number)
        )
    )
    assert [item.attempt_number for item in attempts] == [1, 2]
    assert attempts[1].status == TaskExecutionStatus.RETRY_SCHEDULED
    second = worker.execute(attempts[1].id)
    assert second.status == TaskExecutionStatus.SUCCEEDED
    assert db_session.get(Command, UUID(command["id"])).status == CommandStatus.COMPLETED


def test_outbox_dispatch_marks_processed_and_tolerates_duplicate_delivery(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    _action, dispatched = create_and_dispatch(
        client, headers, str(tasks[0]["id"]), "internal.echo", {"text": "outbox"}
    )

    class Sender:
        def __init__(self) -> None:
            self.ids: list[UUID] = []

        def send_execution(self, execution_id: UUID, _session: Session) -> None:
            self.ids.append(execution_id)

    sender = Sender()
    dispatcher = OutboxDispatcher(session_factory, sender=sender)
    assert dispatcher.dispatch_once() == 1
    assert sender.ids == [UUID(dispatched["execution"]["id"])]
    assert dispatcher.dispatch_once() == 0
    event = db_session.scalar(select(OutboxEvent))
    assert event.status == OutboxStatus.PROCESSED


def test_dependencies_reject_self_and_cycles_and_block_dispatch(
    client: TestClient, db_session: Session
) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session, task_count=2)
    first, second = tasks
    self_dependency = client.post(
        f"/api/v1/tasks/{first['id']}/dependencies",
        headers=headers,
        json={"depends_on_task_id": first["id"]},
    )
    assert self_dependency.status_code == 409
    accepted = client.post(
        f"/api/v1/tasks/{first['id']}/dependencies",
        headers=headers,
        json={"depends_on_task_id": second["id"]},
    )
    assert accepted.status_code == 201
    cycle = client.post(
        f"/api/v1/tasks/{second['id']}/dependencies",
        headers=headers,
        json={"depends_on_task_id": first["id"]},
    )
    assert cycle.status_code == 409

    action = client.post(
        f"/api/v1/tasks/{first['id']}/actions",
        headers=headers,
        json={"tool_name": "internal.echo", "input_payload": {"text": "blocked"}},
    )
    blocked = client.post(f"/api/v1/actions/{action.json()['id']}/dispatch", headers=headers)
    assert blocked.status_code == 409
    assert db_session.get(Task, UUID(first["id"])).status == TaskStatus.BLOCKED


def test_execution_resources_are_hidden_from_other_users(
    client: TestClient, db_session: Session
) -> None:
    owner, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    action, dispatched = create_and_dispatch(
        client, owner, str(tasks[0]["id"]), "internal.echo", {"text": "private"}
    )
    other = register(client, "other-execution@example.com")

    assert client.get(f"/api/v1/actions/{action['id']}", headers=other).status_code == 404
    assert (
        client.get(f"/api/v1/executions/{dispatched['execution']['id']}", headers=other).status_code
        == 404
    )
    assert client.get("/api/v1/approvals", headers=other).json() == []


def test_execution_risk_policy_never_lowers_payload_risk() -> None:
    from app.execution.policies import ExecutionRiskPolicy

    policy = ExecutionRiskPolicy()
    assert policy.evaluate({"description": "publish this post"}) == RiskLevel.YELLOW
    assert policy.evaluate({"description": "transfer money"}) == RiskLevel.RED
    assert policy.evaluate({"description": "draft internally"}) == RiskLevel.GREEN


def test_change_after_approval_is_refused_by_worker(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    action, dispatched = create_and_dispatch(
        client,
        headers,
        str(tasks[0]["id"]),
        "internal.simulate_external_action",
        {"action": "publish_post", "description": "Approved payload"},
    )
    approved = client.post(
        f"/api/v1/approvals/{dispatched['approval']['id']}/approve",
        headers=headers,
        json={"confirm_high_risk": False},
    )
    execution_id = UUID(approved.json()["execution"]["id"])
    stored = db_session.get(TaskAction, UUID(action["id"]))
    stored.input_payload = {"action": "publish_post", "description": "Changed after approval"}
    db_session.commit()

    result = ExecutionWorker(
        session_factory, retry_policy=RetryPolicy(system_max_retries=3)
    ).execute(execution_id)
    assert result is None
    db_session.expire_all()
    execution = db_session.get(TaskExecution, execution_id)
    assert execution.status == TaskExecutionStatus.CANCELLED
    assert execution.error_code == "action_fingerprint_changed"


def test_command_cancel_propagates_to_unstarted_execution(
    client: TestClient, db_session: Session
) -> None:
    headers, command, _plan, tasks = setup_ready_tasks(client, db_session)
    action, dispatched = create_and_dispatch(
        client, headers, str(tasks[0]["id"]), "internal.echo", {"text": "cancel"}
    )
    response = client.post(f"/api/v1/commands/{command['id']}/cancel", headers=headers)
    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(TaskAction, UUID(action["id"])).status == TaskActionStatus.CANCELLED
    assert (
        db_session.get(TaskExecution, UUID(dispatched["execution"]["id"])).status
        == TaskExecutionStatus.CANCELLED
    )
    assert db_session.get(Task, UUID(tasks[0]["id"])).status == TaskStatus.CANCELLED


def test_outbox_exhaustion_remains_failed_without_infinite_reclaim(
    client: TestClient,
    db_session: Session,
    session_factory,
) -> None:
    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    create_and_dispatch(
        client, headers, str(tasks[0]["id"]), "internal.echo", {"text": "queue failure"}
    )

    class FailingSender:
        def send_execution(self, _execution_id: UUID, _session: Session) -> None:
            raise RuntimeError("broker unavailable")

    dispatcher = OutboxDispatcher(session_factory, sender=FailingSender(), max_attempts=1)
    assert dispatcher.dispatch_once() == 0
    db_session.expire_all()
    event = db_session.scalar(select(OutboxEvent))
    assert event.status == OutboxStatus.FAILED
    assert event.next_attempt_at is None
    assert event.last_error == "Queue dispatch failed"
    assert dispatcher.dispatch_once() == 0


def test_celery_sender_applies_registered_tool_timeout(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.execution.celery_app import celery_app
    from app.execution.dispatcher import CeleryExecutionSender

    headers, _command, _plan, tasks = setup_ready_tasks(client, db_session)
    _action, dispatched = create_and_dispatch(
        client, headers, str(tasks[0]["id"]), "internal.echo", {"text": "timeout"}
    )
    calls: list[dict[str, object]] = []

    def fake_send_task(name: str, **kwargs) -> None:
        calls.append({"name": name, **kwargs})

    monkeypatch.setattr(celery_app, "send_task", fake_send_task)
    CeleryExecutionSender().send_execution(UUID(dispatched["execution"]["id"]), db_session)
    assert calls[0]["soft_time_limit"] == 10
    assert calls[0]["time_limit"] == 15
