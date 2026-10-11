from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.approval_request import ApprovalRequest
from app.models.supervisor_run import SupervisorRun
from app.models.task_action import TaskAction
from app.models.user import User
from app.models.workflow_enums import ActorType, RiskLevel, SupervisorRunStatus

PASSWORD = "ConversationPassword123!"


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Conversation User",
            "terms_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert response.status_code == 202
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_conversation_turns_create_real_commands(client: TestClient) -> None:
    headers = register(client, "conversation@example.com")

    created = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"message": "Prepare a launch plan for our new service"},
    )
    assert created.status_code == 201
    first = created.json()
    assert first["conversation"]["title"] == "Prepare a launch plan for our new service"
    assert [message["role"] for message in first["messages"]] == ["user", "kiko"]
    assert first["command"]["input"] == "Prepare a launch plan for our new service"
    assert first["command"]["conversation_id"] == first["conversation"]["id"]
    assert first["messages"][1]["command_id"] == first["command"]["id"]

    follow_up = client.post(
        f"/api/v1/conversations/{first['conversation']['id']}/messages",
        headers=headers,
        json={"message": "Focus the plan on existing B2B clients"},
    )
    assert follow_up.status_code == 200
    second = follow_up.json()
    assert second["command"]["conversation_id"] == first["conversation"]["id"]

    detail = client.get(f"/api/v1/conversations/{first['conversation']['id']}", headers=headers)
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "kiko",
        "user",
        "kiko",
    ]
    commands = client.get("/api/v1/commands", headers=headers)
    assert commands.status_code == 200
    assert {item["id"] for item in commands.json()} == {
        first["command"]["id"],
        second["command"]["id"],
    }


def test_conversation_projects_operational_state(client: TestClient, db_session: Session) -> None:
    headers = register(client, "conversation-operations@example.com")
    db_session.add(Agent(id="marketing", name="Marketing", description="Test agent"))
    db_session.commit()
    created = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"message": "Prepare a governed campaign"},
    ).json()
    command_id = created["command"]["id"]
    conversation_id = created["conversation"]["id"]
    plan = client.post(
        f"/api/v1/commands/{command_id}/plan",
        headers=headers,
        json={"title": "Campaign plan", "objective": "Generate qualified demand"},
    )
    assert plan.status_code == 201
    task = client.post(
        f"/api/v1/plans/{plan.json()['id']}/tasks",
        headers=headers,
        json={
            "agent_id": "marketing",
            "title": "Draft campaign",
            "instructions": "Prepare the governed campaign draft.",
            "priority": "normal",
            "risk_level": "green",
            "sequence": 1,
        },
    )
    assert task.status_code == 201
    user = db_session.scalar(
        select(User).where(User.email == "conversation-operations@example.com")
    )
    assert user is not None
    action = TaskAction(
        task_id=UUID(task.json()["id"]),
        tool_name="marketing.prepare",
        tool_version="1",
        input_payload={},
        risk_level=RiskLevel.YELLOW,
        created_by_type=ActorType.SUPERVISOR,
        action_fingerprint="a" * 64,
    )
    db_session.add(action)
    db_session.flush()
    db_session.add_all(
        [
            ApprovalRequest(
                user_id=user.id,
                task_id=UUID(task.json()["id"]),
                task_action_id=action.id,
                risk_level=RiskLevel.YELLOW,
                title="Approve campaign draft",
                description="Review before publishing.",
                action_fingerprint=action.action_fingerprint,
            ),
            SupervisorRun(
                command_id=UUID(command_id),
                user_id=user.id,
                status=SupervisorRunStatus.COMPLETED,
                provider="test",
                model="test-model",
                prompt_version="test-v1",
            ),
        ]
    )
    db_session.commit()

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 200
    operation = detail.json()["operations"][0]
    assert operation["command"]["id"] == command_id
    assert operation["command"]["status"] == "planning"
    assert operation["plan"] == {
        "id": plan.json()["id"],
        "title": "Campaign plan",
        "objective": "Generate qualified demand",
        "status": "draft",
    }
    assert operation["task_counts"] == {"pending": 1}
    assert operation["supervisor_status"] == "completed"
    assert operation["pending_approvals"] == 1
    assert operation["latest_error"] is None


def test_conversations_are_workspace_isolated(client: TestClient) -> None:
    owner = register(client, "conversation-owner@example.com")
    outsider = register(client, "conversation-outsider@example.com")
    created = client.post(
        "/api/v1/conversations",
        headers=owner,
        json={"message": "Private company objective"},
    ).json()
    conversation_id = created["conversation"]["id"]

    assert client.get("/api/v1/conversations", headers=outsider).json() == []
    assert (
        client.get(f"/api/v1/conversations/{conversation_id}", headers=outsider).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=outsider,
            json={"message": "Attempted cross-tenant message"},
        ).status_code
        == 404
    )


def test_conversation_validation_and_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/conversations", json={"message": "Hello"}).status_code == 401
    headers = register(client, "conversation-validation@example.com")
    assert (
        client.post("/api/v1/conversations", headers=headers, json={"message": "   "}).status_code
        == 422
    )
