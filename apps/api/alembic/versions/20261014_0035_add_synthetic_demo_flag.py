"""Add an explicit safety boundary for synthetic demo workspaces."""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0035"
down_revision = "20261014_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "is_synthetic_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_workspaces_is_synthetic_demo", "workspaces", ["is_synthetic_demo"])


def downgrade() -> None:
    op.drop_index("ix_workspaces_is_synthetic_demo", table_name="workspaces")
    op.drop_column("workspaces", "is_synthetic_demo")
