from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "agent-api",
        "message": "Pixart Agent API",
    }


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "agent-api",
    }


def test_agents() -> None:
    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    assert [agent["id"] for agent in response.json()] == [
        "supervisor",
        "marketing",
        "sales",
        "support",
        "development",
    ]
