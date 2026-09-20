"""Seed an explicitly synthetic Sporting CP Demo knowledge workspace."""

import argparse

from sqlalchemy import select

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeItem, KnowledgeRevision, Workspace, WorkspaceMember
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


def seed(user_email: str) -> str:
    with SessionLocal() as session, session.begin():
        user = session.scalar(select(User).where(User.email == user_email.strip().lower()))
        if user is None:
            raise RuntimeError("Seed user does not exist")
        existing = session.scalar(select(Workspace).where(Workspace.slug == SLUG))
        if existing is not None:
            return str(existing.id)
        workspace = Workspace(name="Sporting CP Demo", slug=SLUG, created_by_user_id=user.id)
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
        return str(workspace.id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", required=True)
    args = parser.parse_args()
    print(seed(args.user_email))


if __name__ == "__main__":
    main()
