"""Add governed marketing content operations.

Revision ID: 20260919_0013
Revises: 20260919_0012
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0013"
down_revision: str | None = "20260919_0012"
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
        "marketing_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('idea', 'active', 'paused', 'completed', 'archived')",
            name="ck_marketing_campaign_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["crm_clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "client_id", "owner_user_id", "status"):
        op.create_index(f"ix_marketing_campaigns_{column}", "marketing_campaigns", [column])
    op.create_index(
        "ix_marketing_campaigns_owner_status",
        "marketing_campaigns",
        ["user_id", "status"],
    )

    op.create_table(
        "marketing_content",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "lifecycle_status IN "
            "('idea', 'draft', 'review', 'approved', 'scheduled', 'published', 'archived')",
            name="ck_marketing_content_lifecycle",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in (
        "user_id",
        "campaign_id",
        "task_id",
        "lifecycle_status",
        "scheduled_for",
    ):
        op.create_index(f"ix_marketing_content_{column}", "marketing_content", [column])
    op.create_index(
        "ix_marketing_content_owner_campaign_status",
        "marketing_content",
        ["user_id", "campaign_id", "lifecycle_status"],
    )
    op.create_index(
        "ix_marketing_content_owner_schedule",
        "marketing_content",
        ["user_id", "scheduled_for"],
    )

    op.create_table(
        "marketing_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("locator", sa.String(2048), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(campaign_id IS NOT NULL) OR (content_id IS NOT NULL)",
            name="ck_marketing_asset_target",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "campaign_id", "content_id"):
        op.create_index(f"ix_marketing_assets_{column}", "marketing_assets", [column])

    op.create_table(
        "marketing_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("external_reference", sa.String(2048), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_id",
            "external_reference",
            name="uq_marketing_publication_reference",
        ),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "content_id"):
        op.create_index(f"ix_marketing_publications_{column}", "marketing_publications", [column])

    op.create_table(
        "marketing_performance_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("value", sa.Numeric(20, 4), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(campaign_id IS NOT NULL) OR (content_id IS NOT NULL)",
            name="ck_marketing_metric_target",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by_action_id"),
    )
    for column in ("user_id", "campaign_id", "content_id"):
        op.create_index(
            f"ix_marketing_performance_metrics_{column}",
            "marketing_performance_metrics",
            [column],
        )
    op.create_index(
        "ix_marketing_metrics_owner_name_measured",
        "marketing_performance_metrics",
        ["user_id", "metric_name", "measured_at"],
    )

    op.create_table(
        "marketing_content_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_action_id"], ["task_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "content_id", "actor_action_id"):
        op.create_index(
            f"ix_marketing_content_history_{column}",
            "marketing_content_history",
            [column],
        )
    op.create_index(
        "ix_marketing_content_history_owner_content",
        "marketing_content_history",
        ["user_id", "content_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_content_history_owner_content",
        table_name="marketing_content_history",
    )
    for column in ("actor_action_id", "content_id", "user_id"):
        op.drop_index(
            f"ix_marketing_content_history_{column}",
            table_name="marketing_content_history",
        )
    op.drop_table("marketing_content_history")

    op.drop_index(
        "ix_marketing_metrics_owner_name_measured",
        table_name="marketing_performance_metrics",
    )
    for column in ("content_id", "campaign_id", "user_id"):
        op.drop_index(
            f"ix_marketing_performance_metrics_{column}",
            table_name="marketing_performance_metrics",
        )
    op.drop_table("marketing_performance_metrics")

    for column in ("content_id", "user_id"):
        op.drop_index(f"ix_marketing_publications_{column}", table_name="marketing_publications")
    op.drop_table("marketing_publications")

    for column in ("content_id", "campaign_id", "user_id"):
        op.drop_index(f"ix_marketing_assets_{column}", table_name="marketing_assets")
    op.drop_table("marketing_assets")

    op.drop_index("ix_marketing_content_owner_schedule", table_name="marketing_content")
    op.drop_index("ix_marketing_content_owner_campaign_status", table_name="marketing_content")
    for column in (
        "scheduled_for",
        "lifecycle_status",
        "task_id",
        "campaign_id",
        "user_id",
    ):
        op.drop_index(f"ix_marketing_content_{column}", table_name="marketing_content")
    op.drop_table("marketing_content")

    op.drop_index("ix_marketing_campaigns_owner_status", table_name="marketing_campaigns")
    for column in ("status", "owner_user_id", "client_id", "user_id"):
        op.drop_index(f"ix_marketing_campaigns_{column}", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")
