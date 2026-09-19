"""Add operational client management.

Revision ID: 20260919_0012
Revises: 20260919_0011
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0012"
down_revision: str | None = "20260919_0011"
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
        "crm_clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "lifecycle_status IN ('prospect', 'active', 'paused', 'former', 'archived')",
            name="ck_crm_client_lifecycle_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_crm_client_owner_organization"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "organization_id", "owner_user_id", "lifecycle_status"):
        op.create_index(f"ix_crm_clients_{column}", "crm_clients", [column])

    op.create_table(
        "crm_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'blocked', 'completed', 'cancelled')",
            name="ck_crm_project_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["crm_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "client_id", "owner_user_id", "status"):
        op.create_index(f"ix_crm_projects_{column}", "crm_projects", [column])
    op.create_index(
        "ix_crm_projects_owner_client_status",
        "crm_projects",
        ["user_id", "client_id", "status"],
    )

    op.create_table(
        "crm_pipelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_crm_pipeline_owner_name"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    op.create_index("ix_crm_pipelines_user_id", "crm_pipelines", ["user_id"])

    op.create_table(
        "crm_pipeline_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("default_probability", sa.Integer(), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "default_probability >= 0 AND default_probability <= 100",
            name="ck_crm_pipeline_stage_probability",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["crm_pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id", "position", name="uq_crm_pipeline_stage_position"),
        sa.UniqueConstraint("pipeline_id", "name", name="uq_crm_pipeline_stage_name"),
    )
    op.create_index("ix_crm_pipeline_stages_user_id", "crm_pipeline_stages", ["user_id"])
    op.create_index("ix_crm_pipeline_stages_pipeline_id", "crm_pipeline_stages", ["pipeline_id"])

    op.create_table(
        "crm_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("stage_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expected_close_on", sa.Date(), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('open', 'won', 'lost', 'cancelled')",
            name="ck_crm_opportunity_status",
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 100",
            name="ck_crm_opportunity_probability",
        ),
        sa.CheckConstraint("amount_minor >= 0", name="ck_crm_opportunity_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["crm_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["crm_pipelines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stage_id"], ["crm_pipeline_stages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in (
        "user_id",
        "client_id",
        "contact_id",
        "pipeline_id",
        "stage_id",
        "owner_user_id",
        "status",
    ):
        op.create_index(f"ix_crm_opportunities_{column}", "crm_opportunities", [column])
    op.create_index(
        "ix_crm_opportunities_owner_client_status",
        "crm_opportunities",
        ["user_id", "client_id", "status"],
    )

    op.create_table(
        "crm_task_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["crm_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["crm_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "task_id", name="uq_crm_task_link_owner_task"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "client_id", "project_id", "task_id"):
        op.create_index(f"ix_crm_task_links_{column}", "crm_task_links", [column])

    op.create_table(
        "crm_record_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("actor_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_record_history_user_id", "crm_record_history", ["user_id"])
    op.create_index(
        "ix_crm_record_history_actor_action_id",
        "crm_record_history",
        ["actor_action_id"],
    )
    op.create_index(
        "ix_crm_record_history_owner_entity",
        "crm_record_history",
        ["user_id", "entity_type", "entity_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_record_history_owner_entity", table_name="crm_record_history")
    op.drop_index("ix_crm_record_history_actor_action_id", table_name="crm_record_history")
    op.drop_index("ix_crm_record_history_user_id", table_name="crm_record_history")
    op.drop_table("crm_record_history")

    for column in ("task_id", "project_id", "client_id", "user_id"):
        op.drop_index(f"ix_crm_task_links_{column}", table_name="crm_task_links")
    op.drop_table("crm_task_links")

    op.drop_index("ix_crm_opportunities_owner_client_status", table_name="crm_opportunities")
    for column in (
        "status",
        "owner_user_id",
        "stage_id",
        "pipeline_id",
        "contact_id",
        "client_id",
        "user_id",
    ):
        op.drop_index(f"ix_crm_opportunities_{column}", table_name="crm_opportunities")
    op.drop_table("crm_opportunities")

    op.drop_index("ix_crm_pipeline_stages_pipeline_id", table_name="crm_pipeline_stages")
    op.drop_index("ix_crm_pipeline_stages_user_id", table_name="crm_pipeline_stages")
    op.drop_table("crm_pipeline_stages")

    op.drop_index("ix_crm_pipelines_user_id", table_name="crm_pipelines")
    op.drop_table("crm_pipelines")

    op.drop_index("ix_crm_projects_owner_client_status", table_name="crm_projects")
    for column in ("status", "owner_user_id", "client_id", "user_id"):
        op.drop_index(f"ix_crm_projects_{column}", table_name="crm_projects")
    op.drop_table("crm_projects")

    for column in ("lifecycle_status", "owner_user_id", "organization_id", "user_id"):
        op.drop_index(f"ix_crm_clients_{column}", table_name="crm_clients")
    op.drop_table("crm_clients")
