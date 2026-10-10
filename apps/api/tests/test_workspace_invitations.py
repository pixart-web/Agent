from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.models.knowledge import WorkspaceMember
from app.models.transactional_email import TransactionalEmailOutbox
from app.security.account_tokens import decrypt_email_payload

from .test_auth import bearer, register


def test_workspace_invitation_lifecycle_and_authorization(client, db_session) -> None:
    owner_body, _ = register(client, email="owner@example.com")
    owner = bearer(owner_body["access_token"])
    invited_body, _ = register(client, email="invitee@example.com")
    invited = bearer(invited_body["access_token"])
    outsider_body, _ = register(client, email="outsider@example.com")
    outsider = bearer(outsider_body["access_token"])

    created = client.post(
        "/api/v1/knowledge/workspaces",
        headers=owner,
        json={"name": "Acme", "slug": "acme-invitations"},
    )
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    hidden = client.get(f"/api/v1/workspaces/{workspace_id}/invitations", headers=outsider)
    assert hidden.status_code == 404

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        headers=owner,
        json={"email": " Invitee@Example.com ", "role": "manager"},
    )
    assert response.status_code == 201
    invitation = response.json()
    assert invitation["email"] == "invitee@example.com"
    assert invitation["role"] == "manager"

    email = db_session.scalar(
        select(TransactionalEmailOutbox)
        .where(TransactionalEmailOutbox.template == "workspace_invitation")
        .order_by(TransactionalEmailOutbox.created_at.desc())
    )
    assert email is not None
    token = decrypt_email_payload(email.encrypted_payload, get_settings().auth_secret_key)["token"]

    wrong_account = client.post(
        "/api/v1/workspaces/invitations/accept",
        headers=outsider,
        json={"token": token},
    )
    assert wrong_account.status_code == 400

    accepted = client.post(
        "/api/v1/workspaces/invitations/accept",
        headers=invited,
        json={"token": token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "manager"
    assert (
        client.post(
            "/api/v1/workspaces/invitations/accept",
            headers=invited,
            json={"token": token},
        ).status_code
        == 400
    )
    member = db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == UUID(accepted.json()["workspace_id"]),
            WorkspaceMember.user_id == UUID(invited_body["user"]["id"]),
        )
    )
    assert member is not None and member.role == "manager"


def test_workspace_invitation_can_be_revoked(client) -> None:
    body, _ = register(client, email="workspace-owner@example.com")
    headers = bearer(body["access_token"])
    workspace = client.post(
        "/api/v1/knowledge/workspaces",
        headers=headers,
        json={"name": "Revoke", "slug": "revoke-invitation"},
    ).json()
    invitation = client.post(
        f"/api/v1/workspaces/{workspace['id']}/invitations",
        headers=headers,
        json={"email": "future@example.com", "role": "viewer"},
    ).json()

    revoked = client.delete(
        f"/api/v1/workspaces/{workspace['id']}/invitations/{invitation['id']}",
        headers=headers,
    )
    assert revoked.status_code == 204
    listed = client.get(f"/api/v1/workspaces/{workspace['id']}/invitations", headers=headers).json()
    assert listed["invitations"][0]["status"] == "revoked"


def test_owner_can_manage_roles_remove_members_and_transfer_ownership(client, db_session) -> None:
    owner_body, _ = register(client, email="lifecycle-owner@example.com")
    owner_headers = bearer(owner_body["access_token"])
    admin_body, _ = register(client, email="lifecycle-admin@example.com")
    admin_headers = bearer(admin_body["access_token"])
    member_body, _ = register(client, email="lifecycle-member@example.com")
    workspace = client.post(
        "/api/v1/knowledge/workspaces",
        headers=owner_headers,
        json={"name": "Lifecycle", "slug": "workspace-lifecycle"},
    ).json()
    workspace_id = UUID(workspace["id"])
    owner_id = UUID(owner_body["user"]["id"])
    admin_id = UUID(admin_body["user"]["id"])
    member_user_id = UUID(member_body["user"]["id"])
    admin = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin_id,
        role="admin",
        created_by_user_id=owner_id,
    )
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=member_user_id,
        role="member",
        created_by_user_id=owner_id,
    )
    db_session.add_all([admin, member])
    db_session.commit()

    assert (
        client.patch(
            f"/api/v1/workspaces/{workspace_id}/members/{member.id}",
            headers=admin_headers,
            json={"role": "manager"},
        ).status_code
        == 200
    )
    owner_member = db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == owner_id,
        )
    )
    assert owner_member is not None
    assert (
        client.delete(
            f"/api/v1/workspaces/{workspace_id}/members/{owner_member.id}",
            headers=admin_headers,
        ).status_code
        == 403
    )

    transferred = client.post(
        f"/api/v1/workspaces/{workspace_id}/ownership-transfer",
        headers=owner_headers,
        json={"user_id": str(admin_id)},
    )
    assert transferred.status_code == 200
    assert transferred.json()["role"] == "owner"
    db_session.expire_all()
    assert db_session.get(WorkspaceMember, owner_member.id).role == "admin"

    removed = client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member.id}",
        headers=admin_headers,
    )
    assert removed.status_code == 204
    assert db_session.get(WorkspaceMember, member.id) is None
