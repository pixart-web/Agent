"""Add governed Calendar integration persistence.

Revision ID: 20260919_0010
Revises: 20260823_0009
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0010"
down_revision: str | None = "20260823_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calendar_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.String(255), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("command_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["integration_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id", "calendar_id", "event_id", name="uq_calendar_reference_event"
        ),
    )
    for column in ("account_id", "task_id", "command_id"):
        op.create_index(f"ix_calendar_references_{column}", "calendar_references", [column])

    op.create_table(
        "calendar_write_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("task_action_id", sa.Uuid(), nullable=False),
        sa.Column("task_execution_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("calendar_id", sa.String(255), nullable=True),
        sa.Column("provider_event_id", sa.String(255), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'delivery_unknown', 'failed')",
            name="ck_calendar_write_records_status",
        ),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'cancel')",
            name="ck_calendar_write_records_operation",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["integration_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_action_id"], ["task_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_execution_id"], ["task_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_action_id", name="uq_calendar_write_action"),
        sa.UniqueConstraint("idempotency_key", name="uq_calendar_write_idempotency"),
    )
    for column in ("user_id", "account_id", "task_action_id", "task_execution_id", "status"):
        op.create_index(f"ix_calendar_write_records_{column}", "calendar_write_records", [column])


def downgrade() -> None:
    op.drop_table("calendar_write_records")
    op.drop_table("calendar_references")
