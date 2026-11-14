"""Align automation run access with workspace ownership.

Revision ID: 20261010_0024
Revises: 20261010_0023
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261010_0024"
down_revision: str | None = "20261010_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_automation_runs_owner_created", table_name="automation_runs")
    op.create_index(
        "ix_automation_runs_automation_created",
        "automation_runs",
        ["automation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_automation_runs_automation_created", table_name="automation_runs")
    op.create_index(
        "ix_automation_runs_owner_created",
        "automation_runs",
        ["user_id", "created_at"],
    )
