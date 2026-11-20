from sqlalchemy import select

from app.core.config import get_settings
from app.models.transactional_email import TransactionalEmailOutbox
from app.security.account_tokens import decrypt_email_payload

from .test_auth import bearer, register


def _join(client, db_session, owner, workspace_id: str, email: str, role: str) -> dict:
    body, _ = register(client, email=email)
    headers = bearer(body["access_token"])
    assert (
        client.post(
            f"/api/v1/workspaces/{workspace_id}/invitations",
            headers=owner,
            json={"email": email, "role": role},
        ).status_code
        == 201
    )
    outbox = db_session.scalar(
        select(TransactionalEmailOutbox)
        .where(TransactionalEmailOutbox.template == "workspace_invitation")
        .order_by(TransactionalEmailOutbox.created_at.desc())
    )
    token = decrypt_email_payload(outbox.encrypted_payload, get_settings().auth_secret_key)["token"]
    assert (
        client.post(
            "/api/v1/workspaces/invitations/accept", headers=headers, json={"token": token}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/workspaces/switch", headers=headers, json={"workspace_id": workspace_id}
        ).status_code
        == 204
    )
    return headers


def test_viewer_is_read_only_and_member_can_edit(client, db_session) -> None:
    owner_body, _ = register(client, email="roles-owner@example.com")
    owner = bearer(owner_body["access_token"])
    created = client.post(
        "/api/v1/knowledge/workspaces",
        headers=owner,
        json={"name": "Roles", "slug": "roles-workspace"},
    )
    workspace_id = created.json()["id"]
    client.post("/api/v1/workspaces/switch", headers=owner, json={"workspace_id": workspace_id})
    command = client.post(
        "/api/v1/commands", headers=owner, json={"input": "Prepare the weekly report"}
    ).json()
    project = client.post("/api/v1/projects", headers=owner, json={"name": "Shared project"}).json()

    viewer = _join(client, db_session, owner, workspace_id, "roles-viewer@example.com", "viewer")
    member = _join(client, db_session, owner, workspace_id, "roles-member@example.com", "member")

    # Viewers read the shared workspace...
    assert client.get("/api/v1/commands", headers=viewer).status_code == 200
    assert client.get(f"/api/v1/projects/{project['id']}", headers=viewer).status_code == 200
    # ...but every write is refused, whatever the router.
    refused = [
        client.post("/api/v1/commands", headers=viewer, json={"input": "Viewer command"}),
        client.post(f"/api/v1/commands/{command['id']}/cancel", headers=viewer, json={}),
        client.post(f"/api/v1/commands/{command['id']}/duplicate", headers=viewer, json={}),
        client.post("/api/v1/conversations", headers=viewer, json={"message": "Hello"}),
        client.post("/api/v1/projects", headers=viewer, json={"name": "Viewer project"}),
        client.post(
            f"/api/v1/projects/{project['id']}/milestones",
            headers=viewer,
            json={"title": "Viewer milestone"},
        ),
    ]
    assert [response.status_code for response in refused] == [403] * len(refused)
    assert all(r.json()["detail"] == "Workspace edit permission is required" for r in refused)

    # Members are editors.
    assert (
        client.post("/api/v1/projects", headers=member, json={"name": "Member project"}).status_code
        == 201
    )
    # The viewer still owns its personal workspace and can write there.
    personal = client.get("/api/v1/auth/me", headers=viewer).json()
    assert personal["id"]


def test_invitee_lands_in_the_team_workspace_without_company_setup(client, db_session) -> None:
    owner_body, _ = register(client, email="team-owner@example.com")
    owner = bearer(owner_body["access_token"])
    completed = client.patch(
        "/api/v1/workspaces/onboarding",
        headers=owner,
        json={
            "step": 8,
            "company_name": "Team Company",
            "company_description": "A team workspace already set up by its owner.",
            "primary_objectives": ["Organize business tasks"],
            "complete": True,
        },
    )
    assert completed.status_code == 200
    workspace_id = completed.json()["workspace_id"]

    body, _ = register(client, email="team-member@example.com")
    member = bearer(body["access_token"])
    assert client.get("/api/v1/auth/me", headers=member).json()["onboarding_completed_at"] is None
    client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        headers=owner,
        json={"email": "team-member@example.com", "role": "member"},
    )
    outbox = db_session.scalar(
        select(TransactionalEmailOutbox)
        .where(TransactionalEmailOutbox.template == "workspace_invitation")
        .order_by(TransactionalEmailOutbox.created_at.desc())
    )
    token = decrypt_email_payload(outbox.encrypted_payload, get_settings().auth_secret_key)["token"]
    assert (
        client.post(
            "/api/v1/workspaces/invitations/accept", headers=member, json={"token": token}
        ).status_code
        == 200
    )

    # No company-setup wizard for the invitee, and the team workspace is the active one.
    assert client.get("/api/v1/auth/me", headers=member).json()["onboarding_completed_at"]
    onboarding = client.get("/api/v1/workspaces/onboarding", headers=member).json()
    assert onboarding["workspace_id"] == workspace_id
    assert onboarding["company_name"] == "Team Company"


def test_member_can_finish_onboarding_without_changing_the_company(client, db_session) -> None:
    owner_body, _ = register(client, email="profile-owner@example.com")
    owner = bearer(owner_body["access_token"])
    profile = {
        "company_name": "Profile Company",
        "company_description": "Configured by the owner.",
        "primary_objectives": ["Organize business tasks"],
    }
    workspace_id = client.patch(
        "/api/v1/workspaces/onboarding",
        headers=owner,
        json={"step": 8, **profile, "complete": True},
    ).json()["workspace_id"]
    member = _join(client, db_session, owner, workspace_id, "profile-member@example.com", "member")
    # A member who joined before invitations completed onboarding is still pending.
    from app.models.user import User

    stuck = db_session.scalar(select(User).where(User.email == "profile-member@example.com"))
    stuck.onboarding_completed_at = None
    db_session.commit()

    changed = client.patch(
        "/api/v1/workspaces/onboarding",
        headers=member,
        json={"step": 8, **profile, "company_name": "Renamed by member", "complete": True},
    )
    assert changed.status_code == 403
    same = client.patch(
        "/api/v1/workspaces/onboarding",
        headers=member,
        json={"step": 8, **profile, "complete": True},
    )
    assert same.status_code == 200
    assert same.json()["completed_at"] is not None
    assert same.json()["company_name"] == "Profile Company"


def test_onboarding_tells_members_the_profile_is_read_only(client, db_session) -> None:
    owner_body, _ = register(client, email="readonly-owner@example.com")
    owner = bearer(owner_body["access_token"])
    profile = {
        "company_name": "Readonly Company",
        "company_description": "Configured by the owner.",
        "primary_objectives": ["Organize business tasks"],
    }
    completed = client.patch(
        "/api/v1/workspaces/onboarding",
        headers=owner,
        json={"step": 8, **profile, "complete": True},
    ).json()
    assert completed["can_edit_company"] is True
    member = _join(
        client,
        db_session,
        owner,
        completed["workspace_id"],
        "readonly-member@example.com",
        "member",
    )
    state = client.get("/api/v1/workspaces/onboarding", headers=member).json()
    assert state["can_edit_company"] is False
    assert state["company_name"] == "Readonly Company"
    # The read-only page finishes with no profile fields at all.
    finished = client.patch(
        "/api/v1/workspaces/onboarding", headers=member, json={"step": 8, "complete": True}
    )
    assert finished.status_code == 200
    assert finished.json()["completed_at"] is not None
