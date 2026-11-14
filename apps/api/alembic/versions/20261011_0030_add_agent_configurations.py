"""Add workspace agent configurations.

Revision ID: 20261011_0030
Revises: 20261011_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0030"
down_revision: str | None = "20261011_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_configurations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("allowed_tools", sa.JSON(), nullable=True),
        sa.Column(
            "approval_policy", sa.String(32), nullable=False, server_default="platform_default"
        ),
        sa.Column("max_actions_per_task", sa.Integer(), nullable=True),
        sa.Column("monthly_token_budget", sa.Integer(), nullable=True),
        sa.Column("knowledge_source_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "workspace_id", "agent_id", name="uq_agent_configurations_workspace_agent"
        ),
        sa.CheckConstraint(
            "approval_policy IN ('platform_default', 'always', 'risk_based')",
            name="ck_agent_configurations_approval_policy",
        ),
    )
    op.create_index(
        "ix_agent_configurations_workspace_id", "agent_configurations", ["workspace_id"]
    )
    op.create_index("ix_agent_configurations_agent_id", "agent_configurations", ["agent_id"])


def downgrade() -> None:
    op.drop_table("agent_configurations")
