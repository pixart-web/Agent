"""Add subscription-ready commercial records.

Revision ID: 20261014_0034
Revises: 20261013_0033
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261014_0034"
down_revision: str | None = "20261013_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    plans = op.create_table(
        "commercial_plans",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_token_limit", sa.Integer(), nullable=False),
        sa.Column("automation_limit", sa.Integer(), nullable=False),
        sa.Column("storage_limit_mb", sa.Integer(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("integrations", sa.JSON(), nullable=False),
        sa.Column("support_level", sa.String(32), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.bulk_insert(
        plans,
        [
            {
                "code": "trial",
                "name": "Trial",
                "description": "Time-limited evaluation",
                "seat_limit": 3,
                "monthly_token_limit": 100000,
                "automation_limit": 5,
                "storage_limit_mb": 250,
                "retention_days": 30,
                "integrations": ["github"],
                "support_level": "self_service",
                "is_public": True,
            },
            {
                "code": "business",
                "name": "Business",
                "description": "Operational teams",
                "seat_limit": 25,
                "monthly_token_limit": 2000000,
                "automation_limit": 100,
                "storage_limit_mb": 10240,
                "retention_days": 365,
                "integrations": ["github", "gmail", "google_calendar", "codex"],
                "support_level": "business",
                "is_public": True,
            },
            {
                "code": "enterprise",
                "name": "Enterprise",
                "description": "Configurable enterprise controls",
                "seat_limit": 1000,
                "monthly_token_limit": 100000000,
                "automation_limit": 10000,
                "storage_limit_mb": 102400,
                "retention_days": 3650,
                "integrations": ["github", "gmail", "google_calendar", "codex"],
                "support_level": "enterprise",
                "is_public": True,
            },
        ],
    )
    op.create_table(
        "workspace_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("billing_provider", sa.String(32)),
        sa.Column("provider_customer_id", sa.String(255)),
        sa.Column("provider_subscription_id", sa.String(255)),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'cancelled', 'expired')",
            name="ck_workspace_subscriptions_status",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_code"], ["commercial_plans.code"], ondelete="RESTRICT"),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_subscriptions_workspace"),
    )
    op.create_index(
        "ix_workspace_subscriptions_workspace_id", "workspace_subscriptions", ["workspace_id"]
    )
    op.create_index(
        "ix_workspace_subscriptions_plan_code", "workspace_subscriptions", ["plan_code"]
    )
    op.create_index("ix_workspace_subscriptions_status", "workspace_subscriptions", ["status"])
    op.create_table(
        "workspace_usage_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("automation_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "workspace_id", "period_start", "period_end", name="uq_workspace_usage_period"
        ),
    )
    op.create_index(
        "ix_workspace_usage_periods_workspace_id", "workspace_usage_periods", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_table("workspace_usage_periods")
    op.drop_table("workspace_subscriptions")
    op.drop_table("commercial_plans")
