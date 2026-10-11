from fastapi.testclient import TestClient

from tests.test_workflow import (
    create_command,
    create_plan,
    create_task,
    register_user,
    seed_agent,
    transition,
)


def test_project_lifecycle_links_and_progress(client: TestClient, db_session) -> None:
    headers = register_user(client, "projects@example.com")
    seed_agent(db_session)

    created = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Commercial launch",
            "description": "Coordinate launch work",
            "status": "active",
            "starts_on": "2026-10-11",
            "due_on": "2026-11-01",
        },
    )
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["progress_percentage"] == 0

    command = create_command(client, headers)
    plan = create_plan(client, headers, str(command["id"]))
    task = create_task(client, headers, str(plan["id"]))

    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            headers=headers,
            json={"resource_id": task["id"]},
        ).status_code
        == 204
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/commands",
            headers=headers,
            json={"resource_id": command["id"]},
        ).status_code
        == 204
    )
    milestone = client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        headers=headers,
        json={"title": "Ready to launch", "due_on": "2026-10-31"},
    )
    assert milestone.status_code == 201

    detail = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["task_count"] == 1
    assert detail.json()["tasks"][0]["id"] == task["id"]
    assert detail.json()["commands"][0]["id"] == command["id"]
    assert len(detail.json()["activity"]) == 4

    transition(client, headers, task["id"], "ready")
    transition(client, headers, task["id"], "running")
    transition(client, headers, task["id"], "completed")
    detail = client.get(f"/api/v1/projects/{project['id']}", headers=headers).json()
    assert detail["progress_percentage"] == 100
    assert detail["completed_task_count"] == 1

    changed = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"status": "completed"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "completed"


def test_projects_are_tenant_isolated_and_validate_dates(client: TestClient) -> None:
    owner = register_user(client, "project-owner@example.com")
    outsider = register_user(client, "project-outsider@example.com")
    invalid = client.post(
        "/api/v1/projects",
        headers=owner,
        json={"name": "Invalid", "starts_on": "2026-11-01", "due_on": "2026-10-01"},
    )
    assert invalid.status_code == 422

    project = client.post(
        "/api/v1/projects", headers=owner, json={"name": "Private roadmap"}
    ).json()
    assert client.get(f"/api/v1/projects/{project['id']}", headers=outsider).status_code == 404
    assert client.get("/api/v1/projects", headers=outsider).json() == []
