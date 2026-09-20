from sqlalchemy import func, select

from app.models.knowledge import KnowledgeRevision
from app.models.user import User
from tests.test_execution_engine import register


def workspace(client, headers, name: str, slug: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/knowledge/workspaces",
        headers=headers,
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 201
    return response.json()


def item(client, headers, workspace_id: str, **overrides) -> dict[str, object]:
    value = {
        "category": "brand_guideline",
        "title": "Sporting Demo brand voice",
        "content": (
            "Sponsor campaigns for Sporting Demo must follow the confident, inclusive "
            "brand rules. Never claim an official Sporting CP affiliation."
        ),
        "sensitivity": "internal",
        "source_type": "synthetic_demo",
        "source_reference": "demo://sporting/brand-v1",
        "provenance": {"dataset": "Sporting CP Demo", "synthetic": True},
    }
    value.update(overrides)
    response = client.post(
        f"/api/v1/knowledge/workspaces/{workspace_id}/items",
        headers=headers,
        json=value,
    )
    assert response.status_code == 201
    return response.json()


def approve(client, headers, workspace_id: str, item_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/knowledge/workspaces/{workspace_id}/items/{item_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_sporting_demo_retrieval_is_approved_relevant_and_workspace_scoped(
    client, db_session
) -> None:
    owner = register(client, "sporting-owner@example.com")
    sporting = workspace(client, owner, "Sporting CP Demo", "sporting-cp-demo")
    other = workspace(client, owner, "Other Demo", "other-demo")

    brand = item(client, owner, sporting["id"])
    approve(client, owner, sporting["id"], brand["id"])
    unrelated = item(
        client,
        owner,
        sporting["id"],
        category="procedure",
        title="Office access",
        content="Badge access for the north office.",
    )
    approve(client, owner, sporting["id"], unrelated["id"])
    draft = item(
        client,
        owner,
        sporting["id"],
        title="Unapproved sponsor instruction",
        content="Sponsor campaign must use an unreviewed slogan.",
    )
    leaked = item(
        client,
        owner,
        other["id"],
        title="Other sponsor rules",
        content="Sponsor campaign for another tenant.",
    )
    approve(client, owner, other["id"], leaked["id"])

    response = client.post(
        f"/api/v1/knowledge/workspaces/{sporting['id']}/search",
        headers=owner,
        json={
            "query": "Prepare a sponsor campaign consistent with Sporting Demo brand rules",
            "limit": 10,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert [value["id"] for value in result["items"]] == [brand["id"]]
    assert draft["id"] not in str(result)
    assert leaked["id"] not in str(result)
    assert "untrusted" in result["trust_notice"].lower()
    assert result["retrieval_method"] == "substring_fallback"
    assert db_session.scalar(select(func.count()).select_from(KnowledgeRevision)) == 7


def test_roles_sensitivity_and_cross_workspace_access(client, db_session) -> None:
    owner = register(client, "workspace-owner@example.com")
    viewer = register(client, "workspace-viewer@example.com")
    stranger = register(client, "workspace-stranger@example.com")
    viewer_user = db_session.scalar(
        select(User).where(User.email == "workspace-viewer@example.com")
    )
    assert viewer_user is not None
    space = workspace(client, owner, "Private Workspace", "private-workspace")
    added = client.post(
        f"/api/v1/knowledge/workspaces/{space['id']}/members",
        headers=owner,
        json={"user_id": str(viewer_user.id), "role": "viewer"},
    )
    assert added.status_code == 201

    public = item(client, owner, space["id"], title="Approved policy", content="Sponsor policy")
    approve(client, owner, space["id"], public["id"])
    confidential = item(
        client,
        owner,
        space["id"],
        title="Confidential policy",
        content="Confidential sponsor policy",
        sensitivity="confidential",
    )
    approve(client, owner, space["id"], confidential["id"])
    restricted = item(
        client,
        owner,
        space["id"],
        title="Restricted policy",
        content="Secret sponsor policy",
        sensitivity="restricted",
    )
    approve(client, owner, space["id"], restricted["id"])

    visible = client.get(f"/api/v1/knowledge/workspaces/{space['id']}/items", headers=viewer)
    assert visible.status_code == 200
    assert [entry["id"] for entry in visible.json()["items"]] == [public["id"]]
    forbidden_create = client.post(
        f"/api/v1/knowledge/workspaces/{space['id']}/items",
        headers=viewer,
        json={
            "category": "policy",
            "title": "No",
            "content": "Viewer write",
            "source_type": "manual",
        },
    )
    assert forbidden_create.status_code == 403
    hidden = client.get(f"/api/v1/knowledge/workspaces/{space['id']}/items", headers=stranger)
    assert hidden.status_code == 404
    assert hidden.json()["detail"] == "Resource not found"


def test_member_can_edit_own_draft_but_cannot_approve(client, db_session) -> None:
    owner = register(client, "knowledge-owner@example.com")
    member = register(client, "knowledge-member@example.com")
    member_user = db_session.scalar(
        select(User).where(User.email == "knowledge-member@example.com")
    )
    assert member_user is not None
    space = workspace(client, owner, "Team", "team-knowledge")
    response = client.post(
        f"/api/v1/knowledge/workspaces/{space['id']}/members",
        headers=owner,
        json={"user_id": str(member_user.id), "role": "member"},
    )
    assert response.status_code == 201
    draft = item(
        client,
        member,
        space["id"],
        category="service",
        title="Sponsorship service",
        content="Initial service notes",
        source_type="operator",
    )
    changed = client.patch(
        f"/api/v1/knowledge/workspaces/{space['id']}/items/{draft['id']}",
        headers=member,
        json={"content": "Reviewed service notes"},
    )
    assert changed.status_code == 200
    denied = client.post(
        f"/api/v1/knowledge/workspaces/{space['id']}/items/{draft['id']}/approve",
        headers=member,
    )
    assert denied.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(KnowledgeRevision)) == 2
