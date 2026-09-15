"""Add governed email integration.

Revision ID: 20260823_0008
Revises: 20260821_0007
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260823_0008"
down_revision: str | None = "20260821_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("email_address", sa.String(320), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "account_type IN ('personal', 'shared', 'system')",
            name="ck_integration_accounts_type",
        ),
        sa.CheckConstraint(
            "status IN ('connected', 'expired', 'revoked', 'error')",
            name="ck_integration_accounts_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "provider", "external_account_id", name="uq_integration_account_owner"
        ),
    )
    for column in ("user_id", "provider", "email_address", "status"):
        op.create_index(f"ix_integration_accounts_{column}", "integration_accounts", [column])

    op.create_table(
        "email_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("command_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["integration_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "message_id", name="uq_email_reference_message"),
    )
    for column in ("account_id", "thread_id", "task_id", "command_id"):
        op.create_index(f"ix_email_references_{column}", "email_references", [column])

    op.create_table(
        "email_send_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("task_action_id", sa.Uuid(), nullable=False),
        sa.Column("task_execution_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'delivery_unknown', 'failed')",
            name="ck_email_send_records_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["integration_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_action_id"], ["task_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_execution_id"], ["task_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_action_id", name="uq_email_send_action"),
        sa.UniqueConstraint("idempotency_key", name="uq_email_send_idempotency"),
    )
    for column in ("user_id", "account_id", "task_action_id", "task_execution_id", "status"):
        op.create_index(f"ix_email_send_records_{column}", "email_send_records", [column])


def downgrade() -> None:
    op.drop_table("email_send_records")
    op.drop_table("email_references")
    op.drop_table("integration_accounts")
