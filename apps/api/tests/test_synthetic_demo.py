from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.automation import Automation
from app.models.crm import CrmContact, CrmOrganization
from app.models.knowledge import Workspace
from app.models.marketing import MarketingCampaign
from app.models.project import Project
from app.models.user import User
from app.scripts import seed_sporting_demo_knowledge as demo


def test_demo_seed_is_explicit_synthetic_and_idempotent(db_session: Session, monkeypatch) -> None:
    user = User(
        email="demo-owner@example.com",
        password_hash="not-used",
        full_name="Demo Owner",
    )
    db_session.add(user)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(demo, "SessionLocal", factory)

    workspace_id = demo.seed(user.email)
    assert demo.seed(user.email) == workspace_id
    with factory() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.id == UUID(workspace_id)))
        assert workspace is not None
        assert workspace.is_synthetic_demo is True
        assert "Synthetic" in workspace.name
        assert session.scalar(
            select(CrmOrganization).where(CrmOrganization.workspace_id == workspace.id)
        )
        assert session.scalar(select(CrmContact).where(CrmContact.workspace_id == workspace.id))
        assert session.scalar(select(Project).where(Project.workspace_id == workspace.id))
        assert session.scalar(
            select(MarketingCampaign).where(MarketingCampaign.workspace_id == workspace.id)
        )
        automation = session.scalar(
            select(Automation).where(Automation.workspace_id == workspace.id)
        )
        assert automation is not None and automation.enabled is False


def test_demo_seed_refuses_reserved_slug_owned_by_real_workspace(
    db_session: Session, monkeypatch
) -> None:
    user = User(
        email="real-owner@example.com",
        password_hash="not-used",
        full_name="Real Owner",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        Workspace(
            name="Real workspace",
            slug=demo.SLUG,
            created_by_user_id=user.id,
            is_synthetic_demo=False,
        )
    )
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(demo, "SessionLocal", factory)

    try:
        demo.seed(user.email, reset=True, confirmation=demo.SLUG)
    except RuntimeError as error:
        assert "non-demo workspace" in str(error)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("A real workspace must never be reset by the demo seeder")
