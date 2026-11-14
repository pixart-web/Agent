from tests.test_execution_engine import register


def test_workspace_and_personal_settings(client) -> None:
    headers = register(client, "workspace-settings@example.com")

    current = client.get("/api/v1/workspaces/settings", headers=headers)
    assert current.status_code == 200, current.text
    original = current.json()
    assert original["role"] == "owner"
    assert original["members"][0]["email"] == "workspace-settings@example.com"

    updated = client.put(
        "/api/v1/workspaces/settings",
        headers=headers,
        json={
            "name": "Pixart Portugal",
            "description": "Commercial AI operations",
            "sector": "Creative technology",
            "country": "PT",
            "website": "https://pixart.pt",
            "branding": {"primary_color": "#111111"},
            "retention_days": 730,
            "ai_monthly_token_limit": 250000,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["country"] == "PT"
    assert updated.json()["retention_days"] == 730

    profile = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "Workspace Owner", "language": "pt-PT", "timezone": "Europe/Lisbon"},
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["language"] == "pt-PT"
    assert profile.json()["timezone"] == "Europe/Lisbon"


def test_workspace_settings_validate_country_and_retention(client) -> None:
    headers = register(client, "invalid-workspace-settings@example.com")
    current = client.get("/api/v1/workspaces/settings", headers=headers).json()
    response = client.put(
        "/api/v1/workspaces/settings",
        headers=headers,
        json={
            "name": current["name"],
            "country": "Portugal",
            "branding": {},
            "retention_days": 1,
        },
    )
    assert response.status_code == 422
