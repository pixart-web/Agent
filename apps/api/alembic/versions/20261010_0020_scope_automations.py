"""Scope automations to workspaces.

Revision ID: 20261010_0020
Revises: 20261010_0019
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0020"
down_revision: str | None = "20261010_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("automations", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_automations_workspace_id",
        "automations",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "UPDATE automations SET workspace_id = users.active_workspace_id "
        "FROM users WHERE automations.user_id = users.id"
    )
    op.alter_column("automations", "workspace_id", nullable=False)
    op.drop_constraint("uq_automations_owner_name", "automations", type_="unique")
    op.drop_index("ix_automations_owner_trigger_enabled", table_name="automations")
    op.create_unique_constraint(
        "uq_automations_workspace_name", "automations", ["workspace_id", "name"]
    )
    op.create_index("ix_automations_workspace_id", "automations", ["workspace_id"])
    op.create_index(
        "ix_automations_workspace_trigger_enabled",
        "automations",
        ["workspace_id", "trigger_type", "enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_automations_workspace_trigger_enabled", table_name="automations")
    op.drop_index("ix_automations_workspace_id", table_name="automations")
    op.drop_constraint("uq_automations_workspace_name", "automations", type_="unique")
    op.create_unique_constraint("uq_automations_owner_name", "automations", ["user_id", "name"])
    op.create_index(
        "ix_automations_owner_trigger_enabled",
        "automations",
        ["user_id", "trigger_type", "enabled"],
    )
    op.drop_constraint("fk_automations_workspace_id", "automations", type_="foreignkey")
    op.drop_column("automations", "workspace_id")
