"""Add governed automation triggers and runs.

Revision ID: 20260920_0014
Revises: 20260919_0013
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0014"
down_revision: str | None = "20260919_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_config", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("command_template", sa.Text(), nullable=False),
        sa.Column("max_depth", sa.Integer(), server_default="3", nullable=False),
        sa.Column("max_runs_per_window", sa.Integer(), server_default="20", nullable=False),
        sa.Column("window_seconds", sa.Integer(), server_default="3600", nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "trigger_type IN ('schedule', 'email_received', 'calendar_event', "
            "'crm_change', 'task_state', 'manual', 'webhook')",
            name="ck_automations_trigger_type",
        ),
        sa.CheckConstraint("max_depth BETWEEN 0 AND 10", name="ck_automations_max_depth"),
        sa.CheckConstraint(
            "max_runs_per_window BETWEEN 1 AND 1000", name="ck_automations_run_budget"
        ),
        sa.CheckConstraint("window_seconds BETWEEN 60 AND 86400", name="ck_automations_window"),
        sa.CheckConstraint("cooldown_seconds BETWEEN 0 AND 86400", name="ck_automations_cooldown"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_automations_owner_name"),
    )
    for column in ("user_id", "enabled", "trigger_type", "next_run_at"):
        op.create_index(f"ix_automations_{column}", "automations", [column])
    op.create_index(
        "ix_automations_owner_trigger_enabled",
        "automations",
        ["user_id", "trigger_type", "enabled"],
    )
    op.create_index(
        "ix_automations_schedule_due",
        "automations",
        ["trigger_type", "enabled", "next_run_at"],
    )

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("automation_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_key", sa.String(255), nullable=False),
        sa.Column("dedupe_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("causation_run_id", sa.Uuid(), nullable=True),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=True),
        sa.Column("skipped_reason", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "trigger_type IN ('schedule', 'email_received', 'calendar_event', "
            "'crm_change', 'task_state', 'manual', 'webhook')",
            name="ck_automation_runs_trigger_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'skipped', 'failed')",
            name="ck_automation_runs_status",
        ),
        sa.CheckConstraint("depth BETWEEN 0 AND 10", name="ck_automation_runs_depth"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["causation_run_id"], ["automation_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("automation_id", "dedupe_key", name="uq_automation_runs_dedupe"),
        sa.UniqueConstraint("command_id", name="uq_automation_runs_command"),
    )
    for column in ("user_id", "automation_id", "status", "causation_run_id", "command_id"):
        op.create_index(f"ix_automation_runs_{column}", "automation_runs", [column])
    op.create_index(
        "ix_automation_runs_owner_created", "automation_runs", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_automation_runs_automation_status",
        "automation_runs",
        ["automation_id", "status"],
    )
    op.create_index("ix_automation_runs_correlation", "automation_runs", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_automation_runs_correlation", table_name="automation_runs")
    op.drop_index("ix_automation_runs_automation_status", table_name="automation_runs")
    op.drop_index("ix_automation_runs_owner_created", table_name="automation_runs")
    for column in ("command_id", "causation_run_id", "status", "automation_id", "user_id"):
        op.drop_index(f"ix_automation_runs_{column}", table_name="automation_runs")
    op.drop_table("automation_runs")

    op.drop_index("ix_automations_schedule_due", table_name="automations")
    op.drop_index("ix_automations_owner_trigger_enabled", table_name="automations")
    for column in ("next_run_at", "trigger_type", "enabled", "user_id"):
        op.drop_index(f"ix_automations_{column}", table_name="automations")
    op.drop_table("automations")
