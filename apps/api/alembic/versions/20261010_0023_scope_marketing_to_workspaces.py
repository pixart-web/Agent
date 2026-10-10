"""Scope marketing campaigns to workspaces.

Revision ID: 20261010_0023
Revises: 20261010_0022
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0023"
down_revision: str | None = "20261010_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("marketing_campaigns", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_campaigns_workspace_id",
        "marketing_campaigns",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "UPDATE marketing_campaigns SET workspace_id = users.active_workspace_id "
        "FROM users WHERE marketing_campaigns.user_id = users.id"
    )
    op.alter_column("marketing_campaigns", "workspace_id", nullable=False)
    op.create_index("ix_marketing_campaigns_workspace_id", "marketing_campaigns", ["workspace_id"])
    op.drop_index("ix_marketing_campaigns_owner_status", table_name="marketing_campaigns")
    op.create_index(
        "ix_marketing_campaigns_workspace_status",
        "marketing_campaigns",
        ["workspace_id", "status"],
    )
    op.drop_index("ix_marketing_content_owner_campaign_status", table_name="marketing_content")
    op.create_index(
        "ix_marketing_content_campaign_status",
        "marketing_content",
        ["campaign_id", "lifecycle_status"],
    )
    op.drop_index("ix_marketing_content_owner_schedule", table_name="marketing_content")
    op.create_index(
        "ix_marketing_content_schedule_campaign",
        "marketing_content",
        ["scheduled_for", "campaign_id"],
    )
    op.drop_index(
        "ix_marketing_metrics_owner_name_measured",
        table_name="marketing_performance_metrics",
    )
    op.create_index(
        "ix_marketing_metrics_campaign_name_measured",
        "marketing_performance_metrics",
        ["campaign_id", "metric_name", "measured_at"],
    )
    op.drop_index(
        "ix_marketing_content_history_owner_content",
        table_name="marketing_content_history",
    )
    op.create_index(
        "ix_marketing_content_history_content",
        "marketing_content_history",
        ["content_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_content_history_content", table_name="marketing_content_history")
    op.create_index(
        "ix_marketing_content_history_owner_content",
        "marketing_content_history",
        ["user_id", "content_id", "created_at"],
    )
    op.drop_index(
        "ix_marketing_metrics_campaign_name_measured",
        table_name="marketing_performance_metrics",
    )
    op.create_index(
        "ix_marketing_metrics_owner_name_measured",
        "marketing_performance_metrics",
        ["user_id", "metric_name", "measured_at"],
    )
    op.drop_index("ix_marketing_content_schedule_campaign", table_name="marketing_content")
    op.create_index(
        "ix_marketing_content_owner_schedule",
        "marketing_content",
        ["user_id", "scheduled_for"],
    )
    op.drop_index("ix_marketing_content_campaign_status", table_name="marketing_content")
    op.create_index(
        "ix_marketing_content_owner_campaign_status",
        "marketing_content",
        ["user_id", "campaign_id", "lifecycle_status"],
    )
    op.drop_index("ix_marketing_campaigns_workspace_status", table_name="marketing_campaigns")
    op.create_index(
        "ix_marketing_campaigns_owner_status",
        "marketing_campaigns",
        ["user_id", "status"],
    )
    op.drop_index("ix_marketing_campaigns_workspace_id", table_name="marketing_campaigns")
    op.drop_constraint(
        "fk_marketing_campaigns_workspace_id", "marketing_campaigns", type_="foreignkey"
    )
    op.drop_column("marketing_campaigns", "workspace_id")
