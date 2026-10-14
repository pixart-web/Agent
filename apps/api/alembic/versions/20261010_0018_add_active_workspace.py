"""Add active workspace context and workspace profile fields.

Revision ID: 20261010_0018
Revises: 20261010_0017
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0018"
down_revision: str | None = "20261010_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "workspaces",
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_check_constraint(
        "ck_workspaces_status", "workspaces", "status IN ('active', 'suspended')"
    )
    op.add_column("users", sa.Column("active_workspace_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_active_workspace_id",
        "users",
        "workspaces",
        ["active_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_active_workspace_id", "users", ["active_workspace_id"])
    op.execute(
        "INSERT INTO workspaces (id, name, slug, description, status, created_by_user_id) "
        "SELECT md5(u.id::text || '\\:workspace')::uuid, u.full_name || '''s Workspace', "
        "'personal-' || replace(u.id::text, '-', ''), NULL, 'active', u.id FROM users u "
        "WHERE NOT EXISTS (SELECT 1 FROM workspace_members wm WHERE wm.user_id = u.id)"
    )
    op.execute(
        "INSERT INTO workspace_members "
        "(id, workspace_id, user_id, role, created_by_user_id) "
        "SELECT md5(u.id::text || '\\:membership')::uuid, "
        "md5(u.id::text || '\\:workspace')::uuid, u.id, 'owner', u.id FROM users u "
        "WHERE NOT EXISTS (SELECT 1 FROM workspace_members wm WHERE wm.user_id = u.id)"
    )
    op.execute(
        "UPDATE users SET active_workspace_id = ("
        "SELECT wm.workspace_id FROM workspace_members wm "
        "WHERE wm.user_id = users.id ORDER BY wm.created_at, wm.id LIMIT 1)"
    )


def downgrade() -> None:
    op.drop_index("ix_users_active_workspace_id", table_name="users")
    op.drop_constraint("fk_users_active_workspace_id", "users", type_="foreignkey")
    op.drop_column("users", "active_workspace_id")
    op.drop_constraint("ck_workspaces_status", "workspaces", type_="check")
    op.drop_column("workspaces", "status")
    op.drop_column("workspaces", "description")
