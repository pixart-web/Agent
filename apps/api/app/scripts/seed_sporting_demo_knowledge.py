"""Seed an explicitly synthetic Sporting CP Demo knowledge workspace."""

import argparse

from sqlalchemy import delete, select

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.automation import Automation
from app.models.crm import CrmContact, CrmContactMethod, CrmOrganization
from app.models.knowledge import KnowledgeItem, KnowledgeRevision, Workspace, WorkspaceMember
from app.models.marketing import MarketingCampaign, MarketingContent
from app.models.project import Project, ProjectActivity
from app.models.user import User

SLUG = "sporting-cp-demo"
DISCLAIMER = "Synthetic demo data. No affiliation with Sporting Clube de Portugal."

ITEMS = (
    (
        "company_profile",
        "Sporting CP Demo profile",
        f"{DISCLAIMER} A fictional sports organization used for safe product demonstrations.",
    ),
    (
        "brand_guideline",
        "Sporting Demo sponsor campaign rules",
        f"{DISCLAIMER} Sponsor campaigns use a confident, inclusive tone, clearly mark demo "
        "assets, avoid official crests and never imply a real commercial relationship.",
    ),
    (
        "procedure",
        "Sponsor campaign review",
        "Every sponsor campaign draft requires owner or admin approval before it can be used "
        "as approved knowledge or prepared for any external channel.",
    ),
)


def seed(user_email: str, *, reset: bool = False, confirmation: str | None = None) -> str:
    with SessionLocal() as session, session.begin():
        user = session.scalar(select(User).where(User.email == user_email.strip().lower()))
        if user is None:
            raise RuntimeError("Seed user does not exist")
        existing = session.scalar(select(Workspace).where(Workspace.slug == SLUG))
        if existing is not None:
            if not existing.is_synthetic_demo:
                raise RuntimeError("Refusing to use a non-demo workspace with the reserved slug")
            if not reset:
                return str(existing.id)
            if confirmation != SLUG:
                raise RuntimeError("Reset confirmation must exactly match the synthetic demo slug")
            session.execute(delete(Workspace).where(Workspace.id == existing.id))
            session.flush()
        workspace = Workspace(
            name="Sporting CP Demo — Synthetic",
            slug=SLUG,
            description=DISCLAIMER,
            primary_objectives=[
                "Coordinate a fictional major event",
                "Prepare a synthetic sponsor campaign",
                "Demonstrate governed operational execution",
            ],
            is_synthetic_demo=True,
            created_by_user_id=user.id,
        )
        session.add(workspace)
        session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role="owner",
                created_by_user_id=user.id,
            )
        )
        for category, title, content in ITEMS:
            item = KnowledgeItem(
                workspace_id=workspace.id,
                created_by_user_id=user.id,
                approved_by_user_id=user.id,
                category=category,
                title=title,
                content=content,
                status="approved",
                sensitivity="internal",
                source_type="synthetic_demo",
                source_reference="demo://sporting-cp",
                provenance={"synthetic": True, "disclaimer": DISCLAIMER},
                approved_at=utc_now(),
            )
            session.add(item)
            session.flush()
            session.add(
                KnowledgeRevision(
                    knowledge_item_id=item.id,
                    workspace_id=workspace.id,
                    actor_user_id=user.id,
                    title=item.title,
                    content=item.content,
                    status=item.status,
                    provenance=item.provenance,
                )
            )
        organization = CrmOrganization(
            workspace_id=workspace.id,
            user_id=user.id,
            name="Northstar Sponsors — Synthetic",
            normalized_name="northstar sponsors — synthetic",
            website="https://example.invalid/northstar",
            source="synthetic_demo",
        )
        session.add(organization)
        session.flush()
        contact = CrmContact(
            workspace_id=workspace.id,
            user_id=user.id,
            organization_id=organization.id,
            full_name="Marta Silva — Synthetic Contact",
            normalized_name="marta silva — synthetic contact",
            job_title="Partnerships Director (fictional)",
            source="synthetic_demo",
        )
        session.add(contact)
        session.flush()
        session.add(
            CrmContactMethod(
                user_id=user.id,
                contact_id=contact.id,
                method_type="email",
                value="marta.silva@example.invalid",
                normalized_value="marta.silva@example.invalid",
                is_primary=True,
            )
        )
        project = Project(
            workspace_id=workspace.id,
            owner_user_id=user.id,
            name="Major event operations — Synthetic",
            description=f"{DISCLAIMER} Cross-team preparation and governance walkthrough.",
            status="active",
        )
        session.add(project)
        session.flush()
        session.add(
            ProjectActivity(
                project_id=project.id,
                actor_user_id=user.id,
                event_type="synthetic_demo_seeded",
                description="Synthetic demo project prepared; no external action occurred.",
            )
        )
        campaign = MarketingCampaign(
            workspace_id=workspace.id,
            user_id=user.id,
            owner_user_id=user.id,
            name="Matchday partner story — Synthetic",
            objective="Prepare a fictional, approval-gated partner campaign.",
            status="active",
        )
        session.add(campaign)
        session.flush()
        session.add(
            MarketingContent(
                user_id=user.id,
                campaign_id=campaign.id,
                content_type="social_post",
                channel="demo_only",
                title="A shared matchday — Synthetic draft",
                body=f"{DISCLAIMER} Draft content for review; it has not been published.",
                lifecycle_status="review",
            )
        )
        session.add(
            Automation(
                user_id=user.id,
                workspace_id=workspace.id,
                name="Synthetic event readiness review",
                description="Manual-only demo automation; disabled until the presenter enables it.",
                enabled=False,
                trigger_type="manual",
                command_template=(
                    "Review synthetic event readiness and prepare an internal summary."
                ),
            )
        )
        return str(workspace.id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", required=True)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--confirm-synthetic-reset")
    args = parser.parse_args()
    print(
        seed(
            args.user_email,
            reset=args.reset,
            confirmation=args.confirm_synthetic_reset,
        )
    )


if __name__ == "__main__":
    main()
