from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.exceptions import AIConfigurationError
from app.api.routes.supervisor import get_supervisor_enqueue
from app.core.time import utc_now
from app.main import app
from app.models.command import Command
from app.models.plan import Plan
from app.models.supervisor_run import SupervisorRun
from app.models.workflow_enums import CommandStatus, SupervisorRunStatus
from app.services import supervisor_tasks
from tests.fakes import FakeLLMProvider
from tests.test_supervisor import (
    proposal,
    provider_override,  # noqa: F401 - pytest fixture
    register_and_create_command,
    result,
    seed_agents,
)


@pytest.fixture
def queued() -> Iterator[list[dict[str, object]]]:
    """Captures enqueued payloads instead of sending them to Celery."""
    payloads: list[dict[str, object]] = []
    app.dependency_overrides[get_supervisor_enqueue] = lambda: payloads.append
    yield payloads
    app.dependency_overrides.pop(get_supervisor_enqueue, None)


def run_worker(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    provider: FakeLLMProvider,
    payload: dict[str, object],
) -> None:
    """Run the Celery task body against the test database and fake model."""

    @contextmanager
    def session_local() -> Iterator[Session]:
        yield db_session

    monkeypatch.setattr(supervisor_tasks, "SessionLocal", session_local)
    monkeypatch.setattr(supervisor_tasks, "get_llm_provider", lambda: provider)
    supervisor_tasks.run_supervisor_payload(payload)


def test_background_planning_answers_at_once_and_the_worker_stores_the_plan(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="background@example.com")

    started = client.post(
        f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={}
    )
    assert started.status_code == 202, started.text
    run = started.json()
    assert run["status"] == "running"
    assert provider_override.calls == []  # no model call in the request
    assert len(queued) == 1 and queued[0]["run_id"] == run["id"]
    # A second start while the first runs is refused.
    again = client.post(
        f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={}
    )
    assert again.status_code == 409

    provider_override.outcomes.append(result(proposal()))
    run_worker(monkeypatch, db_session, provider_override, queued[0])

    runs = client.get(f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers)
    assert runs.json()[0]["status"] == "completed"
    plans = client.get(f"/api/v1/commands/{command['id']}/plans", headers=headers).json()
    assert len(plans) == 1 and plans[0]["status"] == "draft"

    # A redelivered task does not plan twice.
    run_worker(monkeypatch, db_session, provider_override, queued[0])
    assert len(provider_override.calls) == 1
    assert (
        len(list(db_session.scalars(select(Plan).where(Plan.command_id == UUID(command["id"])))))
        == 1
    )


def test_background_revision_with_feedback_replaces_the_draft(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="revise@example.com")
    client.post(f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={})
    provider_override.outcomes.append(result(proposal()))
    run_worker(monkeypatch, db_session, provider_override, queued[0])

    revised = client.post(
        f"/api/v1/commands/{command['id']}/supervisor-runs",
        headers=headers,
        json={"feedback": "  Focus on Lisbon instead.  "},
    )
    assert revised.status_code == 202
    assert revised.json()["user_feedback"] == "Focus on Lisbon instead."
    provider_override.outcomes.append(result(proposal(title="Lisbon plan")))
    run_worker(monkeypatch, db_session, provider_override, queued[1])

    plans = client.get(f"/api/v1/commands/{command['id']}/plans", headers=headers).json()
    current = [plan for plan in plans if plan["is_current"]]
    assert [plan["title"] for plan in current] == ["Lisbon plan"]
    assert "Focus on Lisbon instead." in str(provider_override.calls[1]["user_prompt"])


def test_model_errors_and_unavailable_runtime_are_recorded_on_the_run(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
    queued: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="bg-error@example.com")
    client.post(f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={})

    def unavailable() -> FakeLLMProvider:
        raise AIConfigurationError("Local AI model gemma4 is not installed")

    @contextmanager
    def session_local() -> Iterator[Session]:
        yield db_session

    monkeypatch.setattr(supervisor_tasks, "SessionLocal", session_local)
    monkeypatch.setattr(supervisor_tasks, "get_llm_provider", unavailable)
    supervisor_tasks.run_supervisor_payload(queued[0])

    run = client.get(f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers).json()[0]
    assert run["status"] == "failed"
    assert run["error_code"] == "AIConfigurationError"
    db_session.expire_all()
    assert db_session.get(Command, UUID(command["id"])).status == CommandStatus.PENDING


def test_enqueue_failure_answers_503_and_frees_the_command(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
) -> None:
    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="no-broker@example.com")

    def broken(_payload: dict[str, object]) -> None:
        raise ConnectionError("broker down")

    app.dependency_overrides[get_supervisor_enqueue] = lambda: broken
    try:
        response = client.post(
            f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={}
        )
    finally:
        app.dependency_overrides.pop(get_supervisor_enqueue, None)
    assert response.status_code == 503
    db_session.expire_all()
    run = db_session.scalar(
        select(SupervisorRun).where(SupervisorRun.command_id == UUID(command["id"]))
    )
    assert run.status == SupervisorRunStatus.FAILED
    assert db_session.get(Command, UUID(command["id"])).status == CommandStatus.PENDING


def test_a_run_abandoned_by_a_dead_process_no_longer_blocks_planning(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
    queued: list[dict[str, object]],
) -> None:
    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="stale@example.com")
    client.post(f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={})
    # The worker died: the run stays "running". Make it older than the model's time budget.
    stale = db_session.scalar(
        select(SupervisorRun).where(SupervisorRun.command_id == UUID(command["id"]))
    )
    stale.created_at = utc_now() - timedelta(hours=2)
    db_session.commit()

    restarted = client.post(
        f"/api/v1/commands/{command['id']}/supervisor-runs", headers=headers, json={}
    )
    assert restarted.status_code == 202, restarted.text
    db_session.expire_all()
    assert db_session.get(SupervisorRun, stale.id).status == SupervisorRunStatus.FAILED
    assert db_session.get(SupervisorRun, stale.id).error_code == "stale_run"


def test_viewers_cannot_start_planning(
    client: TestClient,
    db_session: Session,
    provider_override: FakeLLMProvider,  # noqa: F811
    queued: list[dict[str, object]],
) -> None:
    from tests.test_workspace_roles import _join

    seed_agents(db_session)
    headers, command = register_and_create_command(client, email="plan-owner@example.com")
    workspace_id = command["workspace_id"]
    viewer = _join(client, db_session, headers, workspace_id, "plan-viewer@example.com", "viewer")
    refused = client.post(
        f"/api/v1/commands/{command['id']}/supervisor-runs", headers=viewer, json={}
    )
    assert refused.status_code == 403
    assert queued == []


def test_worker_time_limit_becomes_a_clear_ai_timeout() -> None:
    from celery.exceptions import SoftTimeLimitExceeded

    from app.ai.exceptions import AIProviderTimeoutError

    class Slow:
        provider_name = "ollama"
        model_name = "gemma4"

        def generate_structured(self, **_kwargs: object) -> object:
            raise SoftTimeLimitExceeded()

    provider = supervisor_tasks.TimeBoundProvider(Slow())  # type: ignore[arg-type]
    assert provider.model_name == "gemma4"
    with pytest.raises(AIProviderTimeoutError, match="time limit"):
        provider.generate_structured(system_prompt="", user_prompt="")
    assert supervisor_tasks.model_budget_seconds(3) == 3 * supervisor_tasks.model_budget_seconds(1)
