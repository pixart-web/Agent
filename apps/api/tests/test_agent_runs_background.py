from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.runner import context_from_payload, context_to_payload
from app.ai.exceptions import AIConfigurationError
from app.ai.provider_factory import get_llm_provider
from app.api.routes.specialized_agents import get_agent_enqueue
from app.core.time import utc_now
from app.main import app
from app.models.agent_run import AgentRun
from app.models.task_action import TaskAction
from app.models.workflow_enums import AgentRunStatus
from app.services import agent_run_tasks
from tests.fakes import FakeLLMProvider
from tests.test_specialized_agents import outcome, proposal, ready_task


@pytest.fixture
def provider() -> Iterator[FakeLLMProvider]:
    fake = FakeLLMProvider([])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_provider, None)


@pytest.fixture
def queued() -> Iterator[list[dict[str, object]]]:
    """Captures enqueued payloads instead of sending them to Celery."""
    payloads: list[dict[str, object]] = []
    app.dependency_overrides[get_agent_enqueue] = lambda: payloads.append
    yield payloads
    app.dependency_overrides.pop(get_agent_enqueue, None)


def run_worker(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    provider: FakeLLMProvider,
    payload: dict[str, object],
) -> None:
    @contextmanager
    def session_local() -> Iterator[Session]:
        yield db_session

    monkeypatch.setattr(agent_run_tasks, "SessionLocal", session_local)
    monkeypatch.setattr(agent_run_tasks, "get_llm_provider", lambda: provider)
    agent_run_tasks.run_agent_payload(payload)


def runs(client: TestClient, headers: dict[str, str], task_id: str) -> list[dict]:
    return client.get(f"/api/v1/tasks/{task_id}/agent-runs", headers=headers).json()


def test_background_agent_run_answers_at_once_and_the_worker_stores_actions(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _command, task = ready_task(client, db_session, "support", "bg-agent@example.com")
    started = client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    assert started.status_code == 202, started.text
    assert started.json()["status"] == "running"
    assert provider.calls == []  # no model call in the request
    assert len(queued) == 1 and queued[0]["run_id"] == started.json()["id"]
    again = client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    assert again.status_code == 409

    provider.outcomes.append(outcome(proposal("internal.echo")))
    run_worker(monkeypatch, db_session, provider, queued[0])
    assert runs(client, headers, task["id"])[0]["status"] == "completed"
    actions = list(
        db_session.scalars(select(TaskAction).where(TaskAction.task_id == UUID(task["id"])))
    )
    assert len(actions) == 1

    # A redelivered task does not run the agent twice.
    run_worker(monkeypatch, db_session, provider, queued[0])
    assert len(provider.calls) == 1


def test_background_rerun_with_feedback_keeps_the_history(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _command, task = ready_task(client, db_session, "support", "bg-rerun@example.com")
    client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    provider.outcomes.append(AIConfigurationError("Local AI runtime is not reachable"))
    run_worker(monkeypatch, db_session, provider, queued[0])
    assert runs(client, headers, task["id"])[0]["status"] == "failed"

    rerun = client.post(
        f"/api/v1/tasks/{task['id']}/agent-runs",
        headers=headers,
        json={"feedback": "  Be brief.  "},
    )
    assert rerun.status_code == 202, rerun.text
    assert rerun.json()["user_feedback"] == "Be brief."
    provider.outcomes.append(outcome(proposal("internal.echo")))
    run_worker(monkeypatch, db_session, provider, queued[1])
    assert [run["status"] for run in runs(client, headers, task["id"])] == [
        "completed",
        "failed",
    ]
    assert "Be brief." in str(provider.calls[-1]["user_prompt"])


def test_unavailable_runtime_in_the_worker_is_recorded_on_the_run(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _command, task = ready_task(client, db_session, "sales", "bg-down@example.com")
    client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})

    def unavailable() -> FakeLLMProvider:
        raise AIConfigurationError("Local AI model gemma4 is not installed")

    @contextmanager
    def session_local() -> Iterator[Session]:
        yield db_session

    monkeypatch.setattr(agent_run_tasks, "SessionLocal", session_local)
    monkeypatch.setattr(agent_run_tasks, "get_llm_provider", unavailable)
    agent_run_tasks.run_agent_payload(queued[0])
    run = runs(client, headers, task["id"])[0]
    assert run["status"] == "failed"
    assert run["error_code"] == "AIConfigurationError"


def test_enqueue_failure_answers_503_and_frees_the_task(
    client: TestClient, db_session: Session, provider: FakeLLMProvider
) -> None:
    headers, _command, task = ready_task(client, db_session, "support", "bg-broker@example.com")

    def broken(_payload: dict[str, object]) -> None:
        raise ConnectionError("broker down")

    app.dependency_overrides[get_agent_enqueue] = lambda: broken
    try:
        response = client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    finally:
        app.dependency_overrides.pop(get_agent_enqueue, None)
    assert response.status_code == 503
    db_session.expire_all()
    run = db_session.scalar(select(AgentRun).where(AgentRun.task_id == UUID(task["id"])))
    assert run.status == AgentRunStatus.FAILED


def test_a_run_abandoned_by_a_dead_worker_no_longer_blocks_the_task(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
) -> None:
    headers, _command, task = ready_task(client, db_session, "support", "bg-stale@example.com")
    client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    stale = db_session.scalar(select(AgentRun).where(AgentRun.task_id == UUID(task["id"])))
    stale.created_at = utc_now() - timedelta(hours=3)
    db_session.commit()

    restarted = client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={})
    assert restarted.status_code == 202, restarted.text
    db_session.expire_all()
    assert db_session.get(AgentRun, stale.id).error_code == "stale_run"


def test_agent_context_survives_the_trip_to_the_worker(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
) -> None:
    import json

    headers, _command, task = ready_task(client, db_session, "marketing", "bg-ctx@example.com")
    client.post(
        f"/api/v1/tasks/{task['id']}/agent-runs", headers=headers, json={"feedback": "Short"}
    )
    payload = json.loads(json.dumps(queued[0]))  # what Celery's JSON serializer delivers
    context = context_from_payload(payload["context"])
    assert context.task_id == UUID(task["id"])
    assert context.feedback == "Short"
    assert context.tool_specs and isinstance(context.tool_specs, tuple)
    assert context_to_payload(context) == payload["context"]


def test_viewers_cannot_start_agent_runs(
    client: TestClient,
    db_session: Session,
    provider: FakeLLMProvider,
    queued: list[dict[str, object]],
) -> None:
    from tests.test_workspace_roles import _join

    headers, command, task = ready_task(client, db_session, "support", "bg-owner@example.com")
    viewer = _join(
        client, db_session, headers, command["workspace_id"], "bg-viewer@example.com", "viewer"
    )
    refused = client.post(f"/api/v1/tasks/{task['id']}/agent-runs", headers=viewer, json={})
    assert refused.status_code == 403
    assert queued == []
