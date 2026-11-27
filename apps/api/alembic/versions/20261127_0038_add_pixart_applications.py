"""Registry of Pixart products Kiko may integrate with (no credentials, no connections yet)."""

import sqlalchemy as sa

from alembic import op

revision = "20261127_0038"
down_revision = "20261127_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pixart_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_version", sa.String(length=32), nullable=True),
        sa.Column("docs_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="unsupported", nullable=False),
        sa.Column("last_health_status", sa.String(length=32), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pixart_applications_key", "pixart_applications", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_pixart_applications_key", table_name="pixart_applications")
    op.drop_table("pixart_applications")
