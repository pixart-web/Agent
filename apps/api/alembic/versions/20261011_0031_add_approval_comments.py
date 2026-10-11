"""Add approval comments.

Revision ID: 20261011_0031
Revises: 20261011_0030
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0031"
down_revision: str | None = "20261011_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_approval_comments_approval_id", "approval_comments", ["approval_id"])
    op.create_index("ix_approval_comments_author_user_id", "approval_comments", ["author_user_id"])


def downgrade() -> None:
    op.drop_table("approval_comments")
