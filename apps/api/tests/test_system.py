from fastapi.testclient import TestClient

from app.main import app
from app.services.readiness_service import ReadinessService, get_readiness_service


def test_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "agent-api",
        "message": "Pixart Agent API",
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "agent-api",
    }


def test_ready_with_healthy_services(client: TestClient) -> None:
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        database_check=lambda: True,
        redis_check=lambda: True,
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "services": {
            "database": "healthy",
            "redis": "healthy",
        },
    }


def test_ready_with_unavailable_database(client: TestClient) -> None:
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        database_check=lambda: False,
        redis_check=lambda: True,
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "services": {
            "database": "unavailable",
            "redis": "healthy",
        },
    }


def test_ready_with_unavailable_redis(client: TestClient) -> None:
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        database_check=lambda: True,
        redis_check=lambda: False,
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "services": {
            "database": "healthy",
            "redis": "unavailable",
        },
    }
