"""Add user-scoped CRM foundation.

Revision ID: 20260919_0011
Revises: 20260919_0010
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0011"
down_revision: str | None = "20260919_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "crm_organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="ck_crm_org_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    op.create_index("ix_crm_organizations_user_id", "crm_organizations", ["user_id"])
    op.create_index("ix_crm_organizations_status", "crm_organizations", ["status"])
    op.create_index(
        "ix_crm_organizations_owner_name", "crm_organizations", ["user_id", "normalized_name"]
    )

    op.create_table(
        "crm_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("website", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="ck_crm_contact_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "organization_id", "status"):
        op.create_index(f"ix_crm_contacts_{column}", "crm_contacts", [column])
    op.create_index("ix_crm_contacts_owner_name", "crm_contacts", ["user_id", "normalized_name"])

    op.create_table(
        "crm_contact_methods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("method_type", sa.String(16), nullable=False),
        sa.Column("value", sa.String(320), nullable=False),
        sa.Column("normalized_value", sa.String(320), nullable=False),
        sa.Column("label", sa.String(64), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("method_type IN ('email', 'phone')", name="ck_crm_contact_method_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "contact_id", "method_type", "normalized_value", name="uq_crm_contact_method"
        ),
    )
    op.create_index("ix_crm_contact_methods_user_id", "crm_contact_methods", ["user_id"])
    op.create_index("ix_crm_contact_methods_contact_id", "crm_contact_methods", ["contact_id"])
    op.create_index(
        "ix_crm_contact_methods_owner_identity",
        "crm_contact_methods",
        ["user_id", "method_type", "normalized_value"],
    )

    op.create_table(
        "crm_organization_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "contact_id", name="uq_crm_organization_member"),
    )
    for column in ("user_id", "organization_id", "contact_id"):
        op.create_index(
            f"ix_crm_organization_members_{column}", "crm_organization_members", [column]
        )

    op.create_table(
        "crm_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("line1", sa.String(255), nullable=False),
        sa.Column("line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=True),
        sa.Column("postal_code", sa.String(32), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(contact_id IS NOT NULL) <> (organization_id IS NOT NULL)",
            name="ck_crm_address_one_owner",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "contact_id", "organization_id"):
        op.create_index(f"ix_crm_addresses_{column}", "crm_addresses", [column])

    op.create_table(
        "crm_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("normalized_name", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_crm_tag_owner_name"),
    )
    op.create_index("ix_crm_tags_user_id", "crm_tags", ["user_id"])

    for table, owner_column, owner_table, constraint in (
        ("crm_contact_tags", "contact_id", "crm_contacts", "uq_crm_contact_tag"),
        (
            "crm_organization_tags",
            "organization_id",
            "crm_organizations",
            "uq_crm_organization_tag",
        ),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column(owner_column, sa.Uuid(), nullable=False),
            sa.Column("tag_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([owner_column], [f"{owner_table}.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["crm_tags.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(owner_column, "tag_id", name=constraint),
        )
        for column in ("user_id", owner_column, "tag_id"):
            op.create_index(f"ix_{table}_{column}", table, [column])

    op.create_table(
        "crm_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(contact_id IS NOT NULL) <> (organization_id IS NOT NULL)",
            name="ck_crm_note_one_target",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "contact_id", "organization_id"):
        op.create_index(f"ix_crm_notes_{column}", "crm_notes", [column])

    op.create_table(
        "crm_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("activity_type", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("email_reference_id", sa.Uuid(), nullable=True),
        sa.Column("calendar_reference_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "contact_id IS NOT NULL OR organization_id IS NOT NULL",
            name="ck_crm_activity_has_target",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["email_reference_id"], ["email_references.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["calendar_reference_id"], ["calendar_references.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "contact_id", "email_reference_id", name="uq_crm_activity_contact_email"
        ),
        sa.UniqueConstraint(
            "contact_id", "calendar_reference_id", name="uq_crm_activity_contact_calendar"
        ),
        sa.UniqueConstraint(
            "organization_id", "email_reference_id", name="uq_crm_activity_org_email"
        ),
        sa.UniqueConstraint(
            "organization_id", "calendar_reference_id", name="uq_crm_activity_org_calendar"
        ),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in (
        "user_id",
        "contact_id",
        "organization_id",
        "activity_type",
        "email_reference_id",
        "calendar_reference_id",
    ):
        op.create_index(f"ix_crm_activities_{column}", "crm_activities", [column])
    op.create_index(
        "ix_crm_activities_owner_occurred", "crm_activities", ["user_id", "occurred_at"]
    )


def downgrade() -> None:
    for table in (
        "crm_activities",
        "crm_notes",
        "crm_organization_tags",
        "crm_contact_tags",
        "crm_tags",
        "crm_addresses",
        "crm_organization_members",
        "crm_contact_methods",
        "crm_contacts",
        "crm_organizations",
    ):
        op.drop_table(table)
