"""Add workspace invitations and manager role.

Revision ID: 20261010_0017
Revises: 20261010_0016
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0017"
down_revision: str | None = "20261010_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_workspace_members_role", "workspace_members", type_="check")
    op.create_check_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        "role IN ('owner', 'admin', 'manager', 'member', 'viewer')",
    )
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'manager', 'member', 'viewer')",
            name="ck_workspace_invitations_role",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name="ck_workspace_invitations_status",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_workspace_invitations_token_hash"),
    )
    op.create_index(
        "ix_workspace_invitations_workspace_id", "workspace_invitations", ["workspace_id"]
    )
    op.create_index("ix_workspace_invitations_email", "workspace_invitations", ["email"])
    op.create_index(
        "ix_workspace_invitations_scope",
        "workspace_invitations",
        ["workspace_id", "status", "expires_at"],
    )
    op.create_index(
        "uq_workspace_invitations_pending_email",
        "workspace_invitations",
        ["workspace_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_workspace_invitations_pending_email",
        table_name="workspace_invitations",
    )
    op.drop_index("ix_workspace_invitations_scope", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_email", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_id", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
    op.drop_constraint("ck_workspace_members_role", "workspace_members", type_="check")
    op.create_check_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        "role IN ('owner', 'admin', 'member', 'viewer')",
    )
