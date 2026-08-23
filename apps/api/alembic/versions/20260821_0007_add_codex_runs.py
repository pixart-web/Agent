"""Add governed Codex runs.

Revision ID: 20260821_0007
Revises: 20260818_0006
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260821_0007"
down_revision: str | None = "20260818_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "codex_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("task_action_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("repository", sa.String(length=200), nullable=False),
        sa.Column("base_branch", sa.String(length=200), nullable=False),
        sa.Column("working_branch", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="created", nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=False),
        sa.Column("runner_type", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("files_changed", sa.JSON(), nullable=False),
        sa.Column("tests_run", sa.JSON(), nullable=False),
        sa.Column("tests_passed", sa.Boolean(), nullable=True),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
        sa.Column("pull_request_url", sa.String(length=500), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('created', 'waiting_approval', 'queued', 'running', "
            "'succeeded', 'failed', 'cancelled')",
            name="ck_codex_runs_status",
        ),
        sa.ForeignKeyConstraint(["task_action_id"], ["task_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_action_id"),
    )
    for column in (
        "task_id",
        "task_action_id",
        "user_id",
        "repository",
        "status",
        "correlation_id",
        "created_at",
    ):
        op.create_index(f"ix_codex_runs_{column}", "codex_runs", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "task_id",
            "task_action_id",
            "user_id",
            "repository",
            "status",
            "correlation_id",
            "created_at",
        )
    ):
        op.drop_index(f"ix_codex_runs_{column}", table_name="codex_runs")
    op.drop_table("codex_runs")
