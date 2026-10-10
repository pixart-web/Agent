"""Scope commands to workspaces.

Revision ID: 20261010_0019
Revises: 20261010_0018
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0019"
down_revision: str | None = "20261010_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("commands", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_commands_workspace_id",
        "commands",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "UPDATE commands SET workspace_id = users.active_workspace_id "
        "FROM users WHERE commands.user_id = users.id"
    )
    op.alter_column("commands", "workspace_id", nullable=False)
    op.create_index("ix_commands_workspace_id", "commands", ["workspace_id"])
    op.create_index(
        "ix_commands_workspace_created", "commands", ["workspace_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_commands_workspace_created", table_name="commands")
    op.drop_index("ix_commands_workspace_id", table_name="commands")
    op.drop_constraint("fk_commands_workspace_id", "commands", type_="foreignkey")
    op.drop_column("commands", "workspace_id")
