from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.services.agent_service import INITIAL_AGENTS, seed_initial_agents

EXPECTED_AGENT_IDS = {
    "supervisor",
    "marketing",
    "sales",
    "support",
    "development",
}


def test_list_agents_from_database(client: TestClient, db_session: Session) -> None:
    seed_initial_agents(db_session)

    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    assert {agent["id"] for agent in response.json()} == EXPECTED_AGENT_IDS
    assert all("created_at" in agent for agent in response.json())
    assert all("updated_at" in agent for agent in response.json())


def test_get_agent(client: TestClient, db_session: Session) -> None:
    seed_initial_agents(db_session)

    response = client.get("/api/v1/agents/supervisor")

    assert response.status_code == 200
    assert response.json()["id"] == "supervisor"
    assert response.json()["name"] == "Supervisor"


def test_get_missing_agent(client: TestClient) -> None:
    response = client.get("/api/v1/agents/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent 'unknown' was not found"}


def test_seed_is_idempotent(db_session: Session) -> None:
    first_result = seed_initial_agents(db_session)
    second_result = seed_initial_agents(db_session)
    agent_count = db_session.scalar(select(func.count()).select_from(Agent))

    assert first_result.created == len(INITIAL_AGENTS)
    assert first_result.updated == 0
    assert second_result.created == 0
    assert second_result.updated == 0
    assert agent_count == len(INITIAL_AGENTS)


def test_seed_updates_only_managed_fields(db_session: Session) -> None:
    seed_initial_agents(db_session)
    supervisor = db_session.get(Agent, "supervisor")
    assert supervisor is not None
    original_created_at = supervisor.created_at
    supervisor.name = "Outdated name"
    db_session.commit()

    result = seed_initial_agents(db_session)
    db_session.refresh(supervisor)

    assert result.created == 0
    assert result.updated == 1
    assert supervisor.name == "Supervisor"
    assert supervisor.created_at == original_created_at
