from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.execution_graph_service import _levels
from tests.test_execution_engine import create_and_dispatch, register, setup_ready_tasks


def test_levels_follow_the_longest_dependency_path() -> None:
    a, b, c, d = "a", "b", "c", "d"
    parents = {b: [a], c: [a, b], d: []}
    assert _levels([a, b, c, d], parents) == {a: 0, b: 1, c: 2, d: 0}
    # A cycle (refused by the API, but possible in old data) lands after everything else.
    assert _levels([a, b], {a: [b], b: [a]}) == {a: 0, b: 0}


def test_graph_places_tasks_by_dependency_and_logs_each_step(
    client: TestClient, db_session: Session
) -> None:
    headers, _command, plan, tasks = setup_ready_tasks(client, db_session, task_count=3)
    first, second, third = tasks
    for task, parent in ((second, first), (third, second)):
        response = client.post(
            f"/api/v1/tasks/{task['id']}/dependencies",
            headers=headers,
            json={"depends_on_task_id": parent["id"]},
        )
        assert response.status_code == 201
    create_and_dispatch(client, headers, first["id"], "internal.echo", {"text": "hello"})

    response = client.get(f"/api/v1/plans/{plan['id']}/execution-graph", headers=headers)
    assert response.status_code == 200
    graph = response.json()
    assert graph["levels"] == 3
    by_id = {node["task_id"]: node for node in graph["nodes"]}
    assert [by_id[t["id"]]["level"] for t in tasks] == [0, 1, 2]
    assert by_id[third["id"]]["depends_on"] == [second["id"]]
    assert {(e["from_task_id"], e["to_task_id"]) for e in graph["edges"]} == {
        (first["id"], second["id"]),
        (second["id"], third["id"]),
    }
    steps = by_id[first["id"]]["steps"]
    kinds = [step["kind"] for step in steps]
    assert "status" in kinds and "execution" in kinds
    execution = next(step for step in steps if step["kind"] == "execution")
    assert execution["title"] == "internal.echo"
    assert execution["detail"] == "#1"
    assert [step["at"] for step in steps] == sorted(step["at"] for step in steps)


def test_graph_is_scoped_to_the_workspace(client: TestClient, db_session: Session) -> None:
    _headers, _command, plan, _tasks = setup_ready_tasks(client, db_session)
    stranger = register(client, "stranger@example.com")
    response = client.get(f"/api/v1/plans/{plan['id']}/execution-graph", headers=stranger)
    assert response.status_code == 404


def test_status_reasons_are_notes_not_errors(client: TestClient, db_session: Session) -> None:
    headers, _command, plan, tasks = setup_ready_tasks(client, db_session)
    graph = client.get(f"/api/v1/plans/{plan['id']}/execution-graph", headers=headers).json()
    status_steps = [s for s in graph["nodes"][0]["steps"] if s["kind"] == "status"]
    assert any(step["note"] for step in status_steps)
    assert all(step["error_message"] is None for step in status_steps)
    assert graph["nodes"][0]["task_id"] == tasks[0]["id"]
