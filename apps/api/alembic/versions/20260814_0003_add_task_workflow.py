"""Add command planning and task workflow.

Revision ID: 20260814_0003
Revises: 20260724_0002
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260814_0003"
down_revision: str | None = "20260724_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMMAND_STATUSES = "'pending', 'planning', 'in_progress', 'completed', 'failed', 'cancelled'"
PLAN_STATUSES = "'draft', 'ready', 'in_progress', 'completed', 'failed', 'cancelled'"
TASK_STATUSES = (
    "'pending', 'ready', 'running', 'waiting_approval', 'completed', "
    "'failed', 'cancelled', 'blocked'"
)
TASK_PRIORITIES = "'low', 'normal', 'high', 'urgent'"
RISK_LEVELS = "'green', 'yellow', 'red'"


def upgrade() -> None:
    op.create_table(
        "commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"status IN ({COMMAND_STATUSES})",
            name="ck_commands_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commands_user_id", "commands", ["user_id"])
    op.create_index("ix_commands_status", "commands", ["status"])
    op.create_index("ix_commands_created_at", "commands", ["created_at"])

    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(f"status IN ({PLAN_STATUSES})", name="ck_plans_status"),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("command_id", name="uq_plans_command_id"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="normal", nullable=False),
        sa.Column("risk_level", sa.String(length=32), server_default="green", nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(f"status IN ({TASK_STATUSES})", name="ck_tasks_status"),
        sa.CheckConstraint(
            f"priority IN ({TASK_PRIORITIES})",
            name="ck_tasks_priority",
        ),
        sa.CheckConstraint(
            f"risk_level IN ({RISK_LEVELS})",
            name="ck_tasks_risk_level",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_tasks_sequence_positive"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_plan_id", "tasks", ["plan_id"])
    op.create_index("ix_tasks_agent_id", "tasks", ["agent_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_plan_sequence", "tasks", ["plan_id", "sequence"])

    op.create_table(
        "task_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"from_status IS NULL OR from_status IN ({TASK_STATUSES})",
            name="ck_task_history_from_status",
        ),
        sa.CheckConstraint(
            f"to_status IN ({TASK_STATUSES})",
            name="ck_task_history_to_status",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_status_history_task_id",
        "task_status_history",
        ["task_id"],
    )
    op.create_index(
        "ix_task_status_history_changed_by_user_id",
        "task_status_history",
        ["changed_by_user_id"],
    )
    op.create_index(
        "ix_task_status_history_created_at",
        "task_status_history",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_status_history_created_at",
        table_name="task_status_history",
    )
    op.drop_index(
        "ix_task_status_history_changed_by_user_id",
        table_name="task_status_history",
    )
    op.drop_index(
        "ix_task_status_history_task_id",
        table_name="task_status_history",
    )
    op.drop_table("task_status_history")
    op.drop_index("ix_tasks_plan_sequence", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_agent_id", table_name="tasks")
    op.drop_index("ix_tasks_plan_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("plans")
    op.drop_index("ix_commands_created_at", table_name="commands")
    op.drop_index("ix_commands_status", table_name="commands")
    op.drop_index("ix_commands_user_id", table_name="commands")
    op.drop_table("commands")
