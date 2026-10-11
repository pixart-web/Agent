"""Add task deadlines.

Revision ID: 20261011_0028
Revises: 20261011_0027
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0028"
down_revision: str | None = "20261011_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])


def downgrade() -> None:
    op.drop_index("ix_tasks_due_at", table_name="tasks")
    op.drop_column("tasks", "due_at")
