from fastapi.testclient import TestClient

PASSWORD = "ConversationPassword123!"


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Conversation User",
            "terms_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert response.status_code == 202
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_conversation_turns_create_real_commands(client: TestClient) -> None:
    headers = register(client, "conversation@example.com")

    created = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"message": "Prepare a launch plan for our new service"},
    )
    assert created.status_code == 201
    first = created.json()
    assert first["conversation"]["title"] == "Prepare a launch plan for our new service"
    assert [message["role"] for message in first["messages"]] == ["user", "kiko"]
    assert first["command"]["input"] == "Prepare a launch plan for our new service"
    assert first["command"]["conversation_id"] == first["conversation"]["id"]
    assert first["messages"][1]["command_id"] == first["command"]["id"]

    follow_up = client.post(
        f"/api/v1/conversations/{first['conversation']['id']}/messages",
        headers=headers,
        json={"message": "Focus the plan on existing B2B clients"},
    )
    assert follow_up.status_code == 200
    second = follow_up.json()
    assert second["command"]["conversation_id"] == first["conversation"]["id"]

    detail = client.get(f"/api/v1/conversations/{first['conversation']['id']}", headers=headers)
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "kiko",
        "user",
        "kiko",
    ]
    commands = client.get("/api/v1/commands", headers=headers)
    assert commands.status_code == 200
    assert {item["id"] for item in commands.json()} == {
        first["command"]["id"],
        second["command"]["id"],
    }


def test_conversations_are_workspace_isolated(client: TestClient) -> None:
    owner = register(client, "conversation-owner@example.com")
    outsider = register(client, "conversation-outsider@example.com")
    created = client.post(
        "/api/v1/conversations",
        headers=owner,
        json={"message": "Private company objective"},
    ).json()
    conversation_id = created["conversation"]["id"]

    assert client.get("/api/v1/conversations", headers=outsider).json() == []
    assert (
        client.get(f"/api/v1/conversations/{conversation_id}", headers=outsider).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=outsider,
            json={"message": "Attempted cross-tenant message"},
        ).status_code
        == 404
    )


def test_conversation_validation_and_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/conversations", json={"message": "Hello"}).status_code == 401
    headers = register(client, "conversation-validation@example.com")
    assert (
        client.post("/api/v1/conversations", headers=headers, json={"message": "   "}).status_code
        == 422
    )
