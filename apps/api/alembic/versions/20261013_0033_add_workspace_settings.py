"""Add user locale and workspace operating settings.

Revision ID: 20261013_0033
Revises: 20261012_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013_0033"
down_revision: str | None = "20261012_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("language", sa.String(16), nullable=False, server_default="en")
    )
    op.add_column(
        "users", sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC")
    )
    op.add_column("workspaces", sa.Column("sector", sa.String(120)))
    op.add_column("workspaces", sa.Column("country", sa.String(2)))
    op.add_column("workspaces", sa.Column("website", sa.String(2048)))
    op.add_column(
        "workspaces", sa.Column("branding", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "workspaces",
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"),
    )
    op.add_column("workspaces", sa.Column("ai_monthly_token_limit", sa.Integer()))


def downgrade() -> None:
    op.drop_column("workspaces", "ai_monthly_token_limit")
    op.drop_column("workspaces", "retention_days")
    op.drop_column("workspaces", "branding")
    op.drop_column("workspaces", "website")
    op.drop_column("workspaces", "country")
    op.drop_column("workspaces", "sector")
    op.drop_column("users", "timezone")
    op.drop_column("users", "language")
