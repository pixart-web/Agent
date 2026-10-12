from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.test_execution_engine import register


def test_marketing_manual_builder_and_lifecycle(client: TestClient) -> None:
    headers = register(client, "marketing-api@example.com")
    campaign_response = client.post(
        "/api/v1/marketing/campaigns",
        headers=headers,
        json={"name": "Autumn launch", "objective": "Create qualified demand"},
    )
    assert campaign_response.status_code == 201, campaign_response.text
    campaign = campaign_response.json()
    activated = client.patch(
        f"/api/v1/marketing/campaigns/{campaign['id']}",
        headers=headers,
        json={"campaign_id": campaign["id"], "status": "active"},
    )
    assert activated.status_code == 200

    content_response = client.post(
        "/api/v1/marketing/content",
        headers=headers,
        json={
            "campaign_id": campaign["id"],
            "content_type": "social_post",
            "channel": "linkedin",
            "title": "Launch announcement",
            "body": "A reviewed product announcement.",
        },
    )
    assert content_response.status_code == 201, content_response.text
    content = content_response.json()
    for target in ("review", "approved"):
        transition = client.post(
            f"/api/v1/marketing/content/{content['id']}/transition",
            headers=headers,
            json={
                "content_id": content["id"],
                "target_status": target,
                "reason": "Operator review",
            },
        )
        assert transition.status_code == 200, transition.text
    scheduled = client.post(
        f"/api/v1/marketing/content/{content['id']}/schedule",
        headers=headers,
        json={
            "content_id": content["id"],
            "scheduled_for": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["lifecycle_status"] == "scheduled"

    invalid = client.patch(
        f"/api/v1/marketing/content/{content['id']}",
        headers=headers,
        json={"content_id": content["id"], "body": "Silent post-approval rewrite"},
    )
    assert invalid.status_code == 409
