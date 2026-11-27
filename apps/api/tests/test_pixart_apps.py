import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.user import User
from app.pixart_apps import service as pixart_service
from app.pixart_apps.service import UnsafeHealthTargetError, health_target
from tests.test_execution_engine import register


def make_superuser(db_session, email: str) -> None:
    user = db_session.scalar(select(User).where(User.email == email))
    user.is_superuser = True
    db_session.commit()


def test_registry_is_managed_by_platform_admins_and_read_by_members(client, db_session) -> None:
    member = register(client, "member@example.com")
    admin = register(client, "pixart-admin@example.com")
    payload = {"key": "web-content-flow", "name": "Web Content Flow"}
    assert (
        client.post("/api/v1/platform-admin/pixart-apps", headers=admin, json=payload).status_code
        == 403
    )
    make_superuser(db_session, "pixart-admin@example.com")

    created = client.post("/api/v1/platform-admin/pixart-apps", headers=admin, json=payload)
    assert created.status_code == 201, created.text
    app = created.json()
    assert app["status"] == "unsupported"
    duplicate = client.post("/api/v1/platform-admin/pixart-apps", headers=admin, json=payload)
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/pixart-apps", headers=member)
    assert listed.status_code == 200
    assert [item["key"] for item in listed.json()] == ["web-content-flow"]
    assert (
        client.patch(
            f"/api/v1/platform-admin/pixart-apps/{app['id']}",
            headers=member,
            json={"status": "available"},
        ).status_code
        == 403
    )

    # "available" needs a recorded contract (address, version, docs).
    premature = client.patch(
        f"/api/v1/platform-admin/pixart-apps/{app['id']}",
        headers=admin,
        json={"status": "available"},
    )
    assert premature.status_code == 409
    contract = client.patch(
        f"/api/v1/platform-admin/pixart-apps/{app['id']}",
        headers=admin,
        json={
            "status": "available",
            "base_url": "https://wcf.example.com/",
            "api_version": "v1",
            "docs_url": "https://wcf.example.com/docs",
        },
    )
    assert contract.status_code == 200, contract.text
    assert contract.json()["base_url"] == "https://wcf.example.com"
    events = {log.event_type for log in db_session.scalars(select(AuditLog))}
    assert {"platform.pixart_app_registered", "platform.pixart_app_updated"} <= events


def test_health_checks_are_off_by_default(client, db_session) -> None:
    admin = register(client, "pixart-admin@example.com")
    make_superuser(db_session, "pixart-admin@example.com")
    app = client.post(
        "/api/v1/platform-admin/pixart-apps",
        headers=admin,
        json={"key": "nodera", "name": "Nodera", "base_url": "https://nodera.example.com"},
    ).json()
    response = client.post(f"/api/v1/platform-admin/pixart-apps/{app['id']}/health", headers=admin)
    assert response.status_code == 409
    assert response.json()["detail"] == "Health checks of Pixart products are disabled"


def test_health_target_refuses_unsafe_addresses(monkeypatch) -> None:
    monkeypatch.setattr(pixart_service, "_host_is_private", lambda host: host == "intranet")
    assert health_target("https://wcf.example.com", False) == "https://wcf.example.com/health"
    for url in ("http://wcf.example.com", "https://intranet", "https://user:pw@wcf.example.com"):
        with pytest.raises(UnsafeHealthTargetError):
            health_target(url, False)
    assert health_target("http://intranet:8080", True) == "http://intranet:8080/health"


def test_health_check_records_the_result(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("PIXART_APPS_HEALTH_CHECKS_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(pixart_service, "_host_is_private", lambda host: False)
    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs["follow_redirects"] is False
        return httpx.Response(200, json={"status": "ok"})

    monkeypatch.setattr(pixart_service.httpx, "get", fake_get)
    try:
        admin = register(client, "pixart-admin@example.com")
        make_superuser(db_session, "pixart-admin@example.com")
        app = client.post(
            "/api/v1/platform-admin/pixart-apps",
            headers=admin,
            json={
                "key": "searchanvil",
                "name": "SearchAnvil",
                "base_url": "https://sa.example.com",
            },
        ).json()
        checked = client.post(
            f"/api/v1/platform-admin/pixart-apps/{app['id']}/health", headers=admin
        )
        assert checked.status_code == 200, checked.text
        assert checked.json()["last_health_status"] == "healthy"
        assert calls == ["https://sa.example.com/health"]
    finally:
        get_settings.cache_clear()
