from uuid import UUID

from sqlalchemy import select

from app.models.notification import NotificationPreference
from app.models.user import User
from app.schemas.execution import TaskActionCreate
from app.services.execution_service import ExecutionService
from tests.test_execution_engine import register
from tests.test_specialized_agents import ready_task


def test_notification_reconciliation_read_state_preferences_and_isolation(
    client, db_session
) -> None:
    headers, _command, task = ready_task(
        client, db_session, "sales", email="notifications@example.com"
    )
    user = db_session.scalar(select(User).where(User.email == "notifications@example.com"))
    action = ExecutionService(db_session).create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(
            tool_name="crm.create_organization",
            tool_version="1",
            input_payload={"name": "Notify Co"},
        ),
    )
    dispatched = ExecutionService(db_session).dispatch(action.id, user.id)
    assert dispatched.approval is not None

    listing = client.get("/api/v1/notifications", headers=headers)
    assert listing.status_code == 200, listing.text
    assert listing.json()["unread_count"] == 1
    notification = listing.json()["notifications"][0]
    assert notification["kind"] == "approval_required"
    assert notification["href"] == "/dashboard/approvals"

    read = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=headers)
    assert read.status_code == 204
    assert (
        client.get("/api/v1/notifications?unread_only=true", headers=headers).json()["unread_count"]
        == 0
    )

    preferences = client.put(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={
            "in_app_enabled": True,
            "email_enabled": False,
            "enabled_kinds": ["execution_failed"],
        },
    )
    assert preferences.status_code == 200
    stored = db_session.get(NotificationPreference, user.id)
    assert stored.enabled_kinds == ["execution_failed"]

    outsider = register(client, "notifications-outsider@example.com")
    assert (
        client.post(
            f"/api/v1/notifications/{notification['id']}/read", headers=outsider
        ).status_code
        == 404
    )
