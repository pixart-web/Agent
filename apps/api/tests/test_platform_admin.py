from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.user import User
from tests.test_execution_engine import register


def test_platform_admin_is_separately_authorized_and_audited(client, db_session) -> None:
    headers = register(client, "platform-admin@example.com")
    assert client.get("/api/v1/platform-admin/overview", headers=headers).status_code == 403

    admin = db_session.scalar(select(User).where(User.email == "platform-admin@example.com"))
    admin.is_superuser = True
    db_session.commit()

    overview = client.get("/api/v1/platform-admin/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["workspace_count"] == 1
    assert overview.json()["subscription_status"] == "not_configured"
    assert all("configured" in item for item in overview.json()["providers"])

    workspaces = client.get("/api/v1/platform-admin/workspaces", headers=headers).json()[
        "workspaces"
    ]
    suspended = client.patch(
        f"/api/v1/platform-admin/workspaces/{workspaces[0]['id']}",
        headers=headers,
        json={"status": "suspended"},
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["status"] == "suspended"
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "platform.workspace_status_changed")
    )

    self_deactivate = client.patch(
        f"/api/v1/platform-admin/users/{admin.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 409


def test_registration_never_grants_platform_admin(client, db_session) -> None:
    register(client, "ordinary-user@example.com")
    user = db_session.scalar(select(User).where(User.email == "ordinary-user@example.com"))
    assert user.is_superuser is False
