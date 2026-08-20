"""Add Supervisor planning, run audit, and Plan versioning.

Revision ID: 20260814_0004
Revises: 20260814_0003
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260814_0004"
down_revision: str | None = "20260814_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUSES = "'pending', 'running', 'completed', 'failed', 'cancelled'"


def upgrade() -> None:
    op.drop_constraint("uq_plans_command_id", "plans", type_="unique")
    op.add_column("plans", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column(
        "plans",
        sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("plans", sa.Column("reasoning_summary", sa.Text(), nullable=True))
    op.add_column("plans", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("plans", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("plans", sa.Column("approved_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_plans_approved_by_user_id_users",
        "plans",
        "users",
        ["approved_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_plans_command_version",
        "plans",
        ["command_id", "version"],
    )
    op.create_index("ix_plans_command_id", "plans", ["command_id"])
    op.create_index(
        "uq_plans_current_command",
        "plans",
        ["command_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "supervisor_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"status IN ({RUN_STATUSES})", name="ck_supervisor_runs_status"),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supervisor_runs_command_id", "supervisor_runs", ["command_id"])
    op.create_index("ix_supervisor_runs_user_id", "supervisor_runs", ["user_id"])
    op.create_index("ix_supervisor_runs_status", "supervisor_runs", ["status"])
    op.create_index("ix_supervisor_runs_created_at", "supervisor_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_supervisor_runs_created_at", table_name="supervisor_runs")
    op.drop_index("ix_supervisor_runs_status", table_name="supervisor_runs")
    op.drop_index("ix_supervisor_runs_user_id", table_name="supervisor_runs")
    op.drop_index("ix_supervisor_runs_command_id", table_name="supervisor_runs")
    op.drop_table("supervisor_runs")

    op.drop_index("uq_plans_current_command", table_name="plans")
    op.drop_index("ix_plans_command_id", table_name="plans")
    op.drop_constraint("uq_plans_command_version", "plans", type_="unique")
    op.drop_constraint("fk_plans_approved_by_user_id_users", "plans", type_="foreignkey")
    op.drop_column("plans", "approved_by_user_id")
    op.drop_column("plans", "approved_at")
    op.drop_column("plans", "rejection_reason")
    op.drop_column("plans", "reasoning_summary")
    op.drop_column("plans", "is_current")
    op.drop_column("plans", "version")
    op.create_unique_constraint("uq_plans_command_id", "plans", ["command_id"])
