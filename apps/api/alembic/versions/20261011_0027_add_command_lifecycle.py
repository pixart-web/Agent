"""Add command archive and duplication lifecycle.

Revision ID: 20261011_0027
Revises: 20261011_0026
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0027"
down_revision: str | None = "20261011_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("commands", sa.Column("duplicated_from_id", sa.Uuid(), nullable=True))
    op.add_column("commands", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_commands_duplicated_from_id",
        "commands",
        "commands",
        ["duplicated_from_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_commands_duplicated_from_id", "commands", ["duplicated_from_id"])
    op.create_index(
        "ix_commands_workspace_archived_created",
        "commands",
        ["workspace_id", "archived_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_commands_workspace_archived_created", table_name="commands")
    op.drop_index("ix_commands_duplicated_from_id", table_name="commands")
    op.drop_constraint("fk_commands_duplicated_from_id", "commands", type_="foreignkey")
    op.drop_column("commands", "archived_at")
    op.drop_column("commands", "duplicated_from_id")
