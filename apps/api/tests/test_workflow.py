from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.task_status_history import TaskStatusHistory

PASSWORD = "securePassword123"


def register_user(
    client: TestClient,
    email: str,
    full_name: str = "Workflow User",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_command(
    client: TestClient,
    headers: dict[str, str],
    text: str = "Create a restaurant campaign",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/commands",
        headers=headers,
        json={"input": text},
    )
    assert response.status_code == 201
    return response.json()


def create_plan(
    client: TestClient,
    headers: dict[str, str],
    command_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/commands/{command_id}/plan",
        headers=headers,
        json={
            "title": "Restaurant campaign",
            "objective": "Generate qualified restaurant leads",
        },
    )
    assert response.status_code == 201
    return response.json()


def seed_agent(db_session: Session, agent_id: str = "marketing") -> None:
    db_session.add(
        Agent(
            id=agent_id,
            name=agent_id.title(),
            description="Test agent",
        )
    )
    db_session.commit()


def create_task(
    client: TestClient,
    headers: dict[str, str],
    plan_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/plans/{plan_id}/tasks",
        headers=headers,
        json={
            "agent_id": "marketing",
            "title": "Draft campaign proposal",
            "instructions": "Define the offer, message, and audience.",
            "priority": "high",
            "risk_level": "green",
            "sequence": 1,
        },
    )
    assert response.status_code == 201
    return response.json()


def transition(
    client: TestClient,
    headers: dict[str, str],
    task_id: str,
    task_status: str,
    reason: str | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        headers=headers,
        json={"status": task_status, "reason": reason},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def workflow(
    client: TestClient,
    db_session: Session,
) -> Iterator[tuple[dict[str, str], dict[str, object], dict[str, object]]]:
    headers = register_user(client, "owner@example.com")
    seed_agent(db_session)
    command = create_command(client, headers)
    plan = create_plan(client, headers, str(command["id"]))
    yield headers, command, plan


def test_create_command_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/commands", json={"input": "Do something"})
    assert response.status_code == 401


def test_create_command_authenticated(client: TestClient) -> None:
    headers = register_user(client, "owner@example.com")
    command = create_command(client, headers)

    assert command["input"] == "Create a restaurant campaign"
    assert command["status"] == "pending"
    assert command["completed_at"] is None


def test_commands_are_isolated_between_users(client: TestClient) -> None:
    owner_headers = register_user(client, "owner@example.com")
    other_headers = register_user(client, "other@example.com", "Other User")
    owner_command = create_command(client, owner_headers, "Owner command")
    create_command(client, other_headers, "Other command")

    owner_list = client.get("/api/v1/commands", headers=owner_headers)
    hidden = client.get(
        f"/api/v1/commands/{owner_command['id']}",
        headers=other_headers,
    )

    assert owner_list.status_code == 200
    assert [item["input"] for item in owner_list.json()] == ["Owner command"]
    assert hidden.status_code == 404


def test_create_plan_and_reject_second_plan(client: TestClient) -> None:
    headers = register_user(client, "owner@example.com")
    command = create_command(client, headers)
    first = create_plan(client, headers, str(command["id"]))
    second = client.post(
        f"/api/v1/commands/{command['id']}/plan",
        headers=headers,
        json={"title": "Duplicate", "objective": "Not allowed"},
    )

    assert first["status"] == "draft"
    assert second.status_code == 409


def test_plan_of_another_user_is_hidden(client: TestClient) -> None:
    owner_headers = register_user(client, "owner@example.com")
    other_headers = register_user(client, "other@example.com", "Other User")
    command = create_command(client, owner_headers)
    create_plan(client, owner_headers, str(command["id"]))

    response = client.get(
        f"/api/v1/commands/{command['id']}/plan",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_create_task_validates_agent_and_writes_initial_history(
    client: TestClient,
    db_session: Session,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, _, plan = workflow
    missing = client.post(
        f"/api/v1/plans/{plan['id']}/tasks",
        headers=headers,
        json={
            "agent_id": "missing",
            "title": "Invalid assignment",
            "instructions": "This agent does not exist",
            "sequence": 1,
        },
    )
    task = create_task(client, headers, str(plan["id"]))
    detail = client.get(f"/api/v1/tasks/{task['id']}", headers=headers)

    assert missing.status_code == 404
    assert task["status"] == "pending"
    assert detail.status_code == 200
    assert detail.json()["history"][0]["from_status"] is None
    assert detail.json()["history"][0]["to_status"] == "pending"
    history = list(db_session.scalars(select(TaskStatusHistory)))
    assert len(history) == 1
    assert history[0].changed_by_user_id is not None


def test_task_of_another_user_is_hidden(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    owner_headers, _, plan = workflow
    task = create_task(client, owner_headers, str(plan["id"]))
    other_headers = register_user(client, "other@example.com", "Other User")

    assert client.get(f"/api/v1/tasks/{task['id']}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/tasks/{task['id']}",
            headers=other_headers,
            json={"title": "Unauthorized"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/tasks/{task['id']}/transition",
            headers=other_headers,
            json={"status": "ready"},
        ).status_code
        == 404
    )


def test_task_patch_cannot_change_status(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, _, plan = workflow
    task = create_task(client, headers, str(plan["id"]))
    response = client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=headers,
        json={"status": "completed"},
    )
    assert response.status_code == 422


def test_valid_transitions_set_timestamps_and_history(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, _, plan = workflow
    task = create_task(client, headers, str(plan["id"]))
    ready = transition(client, headers, str(task["id"]), "ready")
    running = transition(
        client,
        headers,
        str(task["id"]),
        "running",
        "Execution started",
    )
    completed = transition(client, headers, str(task["id"]), "completed")

    assert ready["status"] == "ready"
    assert running["started_at"] is not None
    assert completed["completed_at"] is not None
    assert [item["to_status"] for item in completed["history"]] == [
        "pending",
        "ready",
        "running",
        "completed",
    ]


def test_invalid_transition_returns_conflict(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, _, plan = workflow
    task = create_task(client, headers, str(plan["id"]))
    response = client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        headers=headers,
        json={"status": "completed"},
    )
    assert response.status_code == 409


def test_failed_task_retry_clears_completion_and_error(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, _, plan = workflow
    task = create_task(client, headers, str(plan["id"]))
    transition(client, headers, str(task["id"]), "ready")
    transition(client, headers, str(task["id"]), "running")
    failed = transition(
        client,
        headers,
        str(task["id"]),
        "failed",
        "Provider unavailable",
    )
    retried = transition(client, headers, str(task["id"]), "ready", "Retry")

    assert failed["completed_at"] is not None
    assert failed["error_message"] == "Provider unavailable"
    assert retried["completed_at"] is None
    assert retried["error_message"] is None


def test_task_and_command_cancellation(
    client: TestClient,
    workflow: tuple[dict[str, str], dict[str, object], dict[str, object]],
) -> None:
    headers, command, plan = workflow
    task = create_task(client, headers, str(plan["id"]))
    cancelled_task = transition(client, headers, str(task["id"]), "cancelled")
    cancelled_command = client.post(
        f"/api/v1/commands/{command['id']}/cancel",
        headers=headers,
    )

    assert cancelled_task["completed_at"] is not None
    assert cancelled_command.status_code == 200
    assert cancelled_command.json()["status"] == "cancelled"
    assert cancelled_command.json()["completed_at"] is not None


def test_command_filters_and_pagination(client: TestClient) -> None:
    headers = register_user(client, "owner@example.com")
    first = create_command(client, headers, "First")
    create_command(client, headers, "Second")
    create_command(client, headers, "Third")
    client.post(f"/api/v1/commands/{first['id']}/cancel", headers=headers)

    cancelled = client.get(
        "/api/v1/commands?status=cancelled&limit=100&offset=0",
        headers=headers,
    )
    page = client.get("/api/v1/commands?limit=1&offset=1", headers=headers)
    invalid_limit = client.get("/api/v1/commands?limit=101", headers=headers)

    assert cancelled.status_code == 200
    assert [item["input"] for item in cancelled.json()] == ["First"]
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert invalid_limit.status_code == 422
