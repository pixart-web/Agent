"""Add execution engine, approvals, outbox, dependencies, and audit.

Revision ID: 20260818_0005
Revises: 20260814_0004
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260818_0005"
down_revision: str | None = "20260814_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTION_STATUSES = (
    "'proposed', 'waiting_approval', 'approved', 'queued', "
    "'running', 'completed', 'failed', 'cancelled'"
)
EXECUTION_STATUSES = (
    "'created', 'queued', 'running', 'succeeded', 'failed', "
    "'retry_scheduled', 'cancelled', 'waiting_approval'"
)
APPROVAL_STATUSES = "'pending', 'approved', 'rejected', 'expired', 'cancelled'"
OUTBOX_STATUSES = "'pending', 'processing', 'processed', 'failed'"
ACTOR_TYPES = "'user', 'kiko', 'supervisor', 'agent', 'worker', 'system'"
RISK_LEVELS = "'green', 'yellow', 'red'"


def upgrade() -> None:
    op.add_column("commands", sa.Column("correlation_id", sa.Uuid(), nullable=True))
    op.create_index("ix_commands_correlation_id", "commands", ["correlation_id"])

    op.create_table(
        "task_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_version", sa.String(length=32), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="proposed", nullable=False),
        sa.Column("created_by_type", sa.String(length=32), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("action_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"risk_level IN ({RISK_LEVELS})", name="ck_task_actions_risk"),
        sa.CheckConstraint(f"status IN ({ACTION_STATUSES})", name="ck_task_actions_status"),
        sa.CheckConstraint(
            f"created_by_type IN ({ACTOR_TYPES})", name="ck_task_actions_actor_type"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_actions_task_id", "task_actions", ["task_id"])
    op.create_index("ix_task_actions_status", "task_actions", ["status"])
    op.create_index("ix_task_actions_correlation_id", "task_actions", ["correlation_id"])
    op.create_index("ix_task_actions_task_created", "task_actions", ["task_id", "created_at"])

    op.create_table(
        "task_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("task_action_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="created", nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_version", sa.String(length=32), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"status IN ({EXECUTION_STATUSES})", name="ck_task_executions_status"),
        sa.CheckConstraint("attempt_number >= 1", name="ck_task_executions_attempt_positive"),
        sa.ForeignKeyConstraint(["task_action_id"], ["task_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_executions_task_id", "task_executions", ["task_id"])
    op.create_index("ix_task_executions_task_action_id", "task_executions", ["task_action_id"])
    op.create_index("ix_task_executions_status", "task_executions", ["status"])
    op.create_index("ix_task_executions_worker_id", "task_executions", ["worker_id"])
    op.create_index("ix_task_executions_created_at", "task_executions", ["created_at"])
    op.create_index("ix_task_executions_correlation_id", "task_executions", ["correlation_id"])
    op.create_index(
        "ix_task_executions_task_attempt",
        "task_executions",
        ["task_id", "attempt_number"],
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("task_action_id", sa.Uuid(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("action_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(f"status IN ({APPROVAL_STATUSES})", name="ck_approval_requests_status"),
        sa.CheckConstraint(f"risk_level IN ({RISK_LEVELS})", name="ck_approval_requests_risk"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_action_id"], ["task_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_user_id", "approval_requests", ["user_id"])
    op.create_index("ix_approval_requests_task_id", "approval_requests", ["task_id"])
    op.create_index("ix_approval_requests_task_action_id", "approval_requests", ["task_action_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_correlation_id", "approval_requests", ["correlation_id"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("depends_on_task_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("task_id <> depends_on_task_id", name="ck_task_dependencies_not_self"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependencies_pair"),
    )
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index(
        "ix_task_dependencies_depends_on_task_id",
        "task_dependencies",
        ["depends_on_task_id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(f"status IN ({OUTBOX_STATUSES})", name="ck_outbox_events_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"])
    op.create_index("ix_outbox_events_next_attempt_at", "outbox_events", ["next_attempt_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(f"actor_type IN ({ACTOR_TYPES})", name="ck_audit_logs_actor_type"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_outbox_events_next_attempt_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index("ix_task_dependencies_depends_on_task_id", table_name="task_dependencies")
    op.drop_index("ix_task_dependencies_task_id", table_name="task_dependencies")
    op.drop_table("task_dependencies")

    op.drop_index("ix_approval_requests_correlation_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_task_action_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_task_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_user_id", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("ix_task_executions_task_attempt", table_name="task_executions")
    op.drop_index("ix_task_executions_correlation_id", table_name="task_executions")
    op.drop_index("ix_task_executions_created_at", table_name="task_executions")
    op.drop_index("ix_task_executions_worker_id", table_name="task_executions")
    op.drop_index("ix_task_executions_status", table_name="task_executions")
    op.drop_index("ix_task_executions_task_action_id", table_name="task_executions")
    op.drop_index("ix_task_executions_task_id", table_name="task_executions")
    op.drop_table("task_executions")

    op.drop_index("ix_task_actions_task_created", table_name="task_actions")
    op.drop_index("ix_task_actions_correlation_id", table_name="task_actions")
    op.drop_index("ix_task_actions_status", table_name="task_actions")
    op.drop_index("ix_task_actions_task_id", table_name="task_actions")
    op.drop_table("task_actions")

    op.drop_index("ix_commands_correlation_id", table_name="commands")
    op.drop_column("commands", "correlation_id")
