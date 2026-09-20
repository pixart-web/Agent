import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "auth_secret_key": "a-secure-random-authentication-secret-9f74a1",
        "auth_cookie_secure": True,
        "auth_rate_limit_fail_open": False,
        "web_origins": "https://kiko.example.org",
        "trusted_hosts": "kiko.example.org",
        "database_url": "postgresql+psycopg://kiko:strong-password@db:5432/kiko",
        "observability_metrics_enabled": True,
        "observability_metrics_token": "metrics-secret-value",
        "ai_provider": "openai",
        "openai_api_key": "test-production-provider-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_request_id_security_headers_and_metrics(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "request-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"

    generated = client.get("/health", headers={"X-Request-ID": "bad request id"})
    assert re.fullmatch(r"[0-9a-f-]{36}", generated.headers["x-request-id"])

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert 'route="/health"' in metrics.text
    assert "kiko_http_requests_total" in metrics.text
    assert 'route="/metrics"' not in metrics.text


def test_valid_production_configuration_is_accepted() -> None:
    settings = production_settings()
    assert settings.trusted_host_list == ["kiko.example.org"]


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"auth_rate_limit_fail_open": True}, "AUTH_RATE_LIMIT_FAIL_OPEN"),
        ({"web_origins": "http://kiko.example.org"}, "HTTPS"),
        ({"trusted_hosts": "*"}, "TRUSTED_HOSTS"),
        ({"observability_metrics_enabled": False}, "observability metrics"),
        ({"observability_metrics_token": None}, "METRICS_TOKEN"),
        ({"openai_api_key": None}, "OPENAI_API_KEY"),
        ({"ai_provider": "fake"}, "fake AI provider"),
        (
            {"database_url": "postgresql+psycopg://agent:agent@db:5432/agent"},
            "default database credentials",
        ),
    ],
)
def test_insecure_production_configuration_is_rejected(
    override: dict[str, object], expected: str
) -> None:
    with pytest.raises(ValidationError, match=expected):
        production_settings(**override)
