"""Add workspaces and governed business knowledge.

Revision ID: 20260920_0015
Revises: 20260920_0014
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0015"
down_revision: str | None = "20260920_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)
    op.create_index("ix_workspaces_created_by_user_id", "workspaces", ["created_by_user_id"])
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')", name="ck_workspace_members_role"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    op.create_index(
        "ix_workspace_members_user_workspace", "workspace_members", ["user_id", "workspace_id"]
    )
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("sensitivity", sa.String(16), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(2048), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "category IN ('company_profile', 'service', 'product', 'policy', 'client', "
            "'project', 'brand_guideline', 'procedure', 'approved_knowledge')",
            name="ck_knowledge_items_category",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'archived')", name="ck_knowledge_items_status"
        ),
        sa.CheckConstraint(
            "sensitivity IN ('internal', 'confidential', 'restricted')",
            name="ck_knowledge_items_sensitivity",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["crm_clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["crm_projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "workspace_id",
        "created_by_user_id",
        "approved_by_user_id",
        "status",
        "client_id",
        "project_id",
    ):
        op.create_index(f"ix_knowledge_items_{column}", "knowledge_items", [column])
    op.create_index(
        "ix_knowledge_items_scope", "knowledge_items", ["workspace_id", "status", "category"]
    )
    op.create_index(
        "ix_knowledge_items_client_project",
        "knowledge_items",
        ["workspace_id", "client_id", "project_id"],
    )
    op.execute(
        "CREATE INDEX ix_knowledge_items_fts ON knowledge_items USING gin "
        "(to_tsvector('simple', title || ' ' || content))"
    )
    op.create_table(
        "knowledge_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_item_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_revisions_knowledge_item_id", "knowledge_revisions", ["knowledge_item_id"]
    )
    op.create_index("ix_knowledge_revisions_workspace_id", "knowledge_revisions", ["workspace_id"])
    op.create_index(
        "ix_knowledge_revisions_item_created",
        "knowledge_revisions",
        ["knowledge_item_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_revisions_item_created", table_name="knowledge_revisions")
    op.drop_index("ix_knowledge_revisions_workspace_id", table_name="knowledge_revisions")
    op.drop_index("ix_knowledge_revisions_knowledge_item_id", table_name="knowledge_revisions")
    op.drop_table("knowledge_revisions")
    op.drop_index("ix_knowledge_items_fts", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_client_project", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_scope", table_name="knowledge_items")
    for column in (
        "project_id",
        "client_id",
        "status",
        "approved_by_user_id",
        "created_by_user_id",
        "workspace_id",
    ):
        op.drop_index(f"ix_knowledge_items_{column}", table_name="knowledge_items")
    op.drop_table("knowledge_items")
    op.drop_index("ix_workspace_members_user_workspace", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index("ix_workspaces_created_by_user_id", table_name="workspaces")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_table("workspaces")
