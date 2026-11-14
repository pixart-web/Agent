from datetime import timedelta

from sqlalchemy import select

from app.core.time import utc_now
from app.models.commercial import WorkspaceSubscription
from app.models.user import User
from tests.test_execution_engine import register


def test_registration_provisions_real_trial_and_entitlements(client, db_session) -> None:
    headers = register(client, "commercial@example.com")

    plans = client.get("/api/v1/commercial/plans", headers=headers)
    assert plans.status_code == 200, plans.text
    assert [item["code"] for item in plans.json()] == ["trial", "business", "enterprise"]
    assert all("price" not in item for item in plans.json())

    subscription = client.get("/api/v1/commercial/subscription", headers=headers)
    assert subscription.status_code == 200, subscription.text
    assert subscription.json()["status"] == "trialing"
    assert subscription.json()["plan"]["code"] == "trial"
    assert subscription.json()["billing_configuration_status"] == "not_configured"
    assert subscription.json()["invoice_links"] == []

    github = client.get("/api/v1/commercial/entitlements/integration:github", headers=headers)
    gmail = client.get("/api/v1/commercial/entitlements/integration:gmail", headers=headers)
    assert github.json()["allowed"] is True
    assert gmail.json()["allowed"] is False


def test_trial_expiry_is_enforced_server_side(client, db_session) -> None:
    headers = register(client, "expired-trial@example.com")
    user = db_session.scalar(select(User).where(User.email == "expired-trial@example.com"))
    subscription = db_session.scalar(
        select(WorkspaceSubscription).where(
            WorkspaceSubscription.workspace_id == user.active_workspace_id
        )
    )
    subscription.current_period_end = utc_now() - timedelta(seconds=1)
    subscription.trial_ends_at = subscription.current_period_end
    db_session.commit()

    decision = client.get("/api/v1/commercial/entitlements/automations", headers=headers)
    assert decision.status_code == 200
    assert decision.json()["allowed"] is False
    assert decision.json()["reason"] == "Subscription is expired"


def test_owner_can_schedule_cancellation_without_fake_charge(client) -> None:
    headers = register(client, "cancel-trial@example.com")
    response = client.post("/api/v1/commercial/subscription/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["cancel_at_period_end"] is True
    assert response.json()["billing_provider"] is None
