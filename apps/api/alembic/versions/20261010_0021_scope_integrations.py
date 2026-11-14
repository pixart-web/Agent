"""Scope integration credentials and OAuth state to workspaces.

Revision ID: 20261010_0021
Revises: 20261010_0020
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0021"
down_revision: str | None = "20261010_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("integration_accounts", "integration_oauth_states"):
        op.add_column(table, sa.Column("workspace_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_workspace_id",
            table,
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.execute(
            f"UPDATE {table} SET workspace_id = users.active_workspace_id "
            f"FROM users WHERE {table}.user_id = users.id"
        )
        op.alter_column(table, "workspace_id", nullable=False)
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])
    op.drop_constraint("uq_integration_account_owner", "integration_accounts", type_="unique")
    op.create_unique_constraint(
        "uq_integration_account_workspace",
        "integration_accounts",
        ["workspace_id", "provider", "external_account_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_integration_account_workspace", "integration_accounts", type_="unique")
    op.create_unique_constraint(
        "uq_integration_account_owner",
        "integration_accounts",
        ["user_id", "provider", "external_account_id"],
    )
    for table in ("integration_oauth_states", "integration_accounts"):
        op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        op.drop_constraint(f"fk_{table}_workspace_id", table, type_="foreignkey")
        op.drop_column(table, "workspace_id")
