from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.audit_log import AuditLog
from app.models.crm import CrmContact, CrmOrganization
from app.models.knowledge import WorkspaceMember
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from tests.test_execution_engine import register


def test_owner_export_is_tenant_scoped_explicit_and_audited(client, db_session: Session) -> None:
    headers = register(client, "export-owner@example.com")
    register(client, "export-other@example.com")
    owner = db_session.scalar(select(User).where(User.email == "export-owner@example.com"))
    other = db_session.scalar(select(User).where(User.email == "export-other@example.com"))
    assert owner is not None and owner.active_workspace_id is not None
    assert other is not None and other.active_workspace_id is not None

    organization = CrmOrganization(
        workspace_id=owner.active_workspace_id,
        user_id=owner.id,
        name="Visible Company",
        normalized_name="visible company",
        website="https://visible.example",
    )
    hidden = CrmOrganization(
        workspace_id=other.active_workspace_id,
        user_id=other.id,
        name="Hidden Company",
        normalized_name="hidden company",
    )
    db_session.add_all([organization, hidden])
    db_session.flush()
    db_session.add(
        CrmContact(
            workspace_id=owner.active_workspace_id,
            user_id=owner.id,
            organization_id=organization.id,
            full_name="=Formula Safe",
            normalized_name="=formula safe",
        )
    )
    db_session.add(
        Project(
            workspace_id=owner.active_workspace_id,
            owner_user_id=owner.id,
            name="Launch",
            description="Real project",
        )
    )
    db_session.commit()

    response = client.get("/api/v1/data-portability/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith('.json"')
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["workspace"]["id"] == str(owner.active_workspace_id)
    assert body["resources"]["organizations"][0]["name"] == "Visible Company"
    assert body["resources"]["projects"][0]["name"] == "Launch"
    serialized = response.text.casefold()
    assert "hidden company" not in serialized
    assert "password_hash" not in serialized
    assert "token_hash" not in serialized
    assert "credential" not in serialized
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "workspace_data_exported")
    )
    assert audit is not None
    assert audit.resource_id == owner.active_workspace_id


def test_csv_export_is_formula_safe_and_requires_one_resource(client, db_session: Session) -> None:
    headers = register(client, "export-csv@example.com")
    user = db_session.scalar(select(User).where(User.email == "export-csv@example.com"))
    assert user is not None and user.active_workspace_id is not None
    db_session.add(
        CrmContact(
            workspace_id=user.active_workspace_id,
            user_id=user.id,
            full_name="=SUM(1,1)",
            normalized_name="=sum(1,1)",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/data-portability/export?resource=contacts&format=csv", headers=headers
    )
    assert response.status_code == 200
    assert "'=SUM(1,1)" in response.text
    assert "attachment" in response.headers["content-disposition"]
    invalid = client.get("/api/v1/data-portability/export?format=csv", headers=headers)
    assert invalid.status_code == 422


def test_workspace_member_cannot_export(client, db_session: Session) -> None:
    headers = register(client, "export-member@example.com")
    user = db_session.scalar(select(User).where(User.email == "export-member@example.com"))
    assert user is not None
    membership = db_session.scalar(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    )
    assert membership is not None
    membership.role = "member"
    db_session.commit()
    assert client.get("/api/v1/data-portability/export", headers=headers).status_code == 403


def test_retention_requires_exact_confirmation_and_preserves_unread(
    client, db_session: Session
) -> None:
    headers = register(client, "retention-owner@example.com")
    user = db_session.scalar(select(User).where(User.email == "retention-owner@example.com"))
    assert user is not None and user.active_workspace_id is not None
    old = utc_now() - timedelta(days=400)
    db_session.add_all(
        [
            Notification(
                workspace_id=user.active_workspace_id,
                user_id=user.id,
                event_key="old-read",
                kind="system",
                title="Old read",
                body="Eligible transient record",
                read_at=old,
                created_at=old,
            ),
            Notification(
                workspace_id=user.active_workspace_id,
                user_id=user.id,
                event_key="old-unread",
                kind="system",
                title="Old unread",
                body="Must be preserved",
                created_at=old,
            ),
        ]
    )
    db_session.commit()
    preview = client.get("/api/v1/data-portability/retention/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["eligible"]["read_notifications"] == 1
    assert "audit_logs" in preview.json()["preserved"]
    rejected = client.post(
        "/api/v1/data-portability/retention/execute",
        headers=headers,
        json={"confirmation": "yes"},
    )
    assert rejected.status_code == 422
    executed = client.post(
        "/api/v1/data-portability/retention/execute",
        headers=headers,
        json={"confirmation": "DELETE_EXPIRED_TRANSIENT_DATA"},
    )
    assert executed.status_code == 200
    assert executed.json()["deleted"]["read_notifications"] == 1
    remaining = list(db_session.scalars(select(Notification)))
    assert [item.event_key for item in remaining] == ["old-unread"]
