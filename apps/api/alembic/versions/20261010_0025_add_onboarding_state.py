"""Add persistent first-run onboarding state.

Revision ID: 20261010_0025
Revises: 20261010_0024
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0025"
down_revision: str | None = "20261010_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("onboarding_step", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE users SET onboarding_step = 8, onboarding_completed_at = CURRENT_TIMESTAMP"
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "primary_objectives",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "primary_objectives")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_step")
