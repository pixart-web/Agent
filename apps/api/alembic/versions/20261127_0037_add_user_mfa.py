"""Add TOTP multi-factor authentication columns to users.

The TOTP seed is stored encrypted with the auth key; recovery codes are stored as SHA-256
hashes; `mfa_last_used_step` prevents a code from being accepted twice.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261127_0037"
down_revision = "20261120_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_secret_encrypted", sa.String(length=512), nullable=True))
    op.add_column(
        "users", sa.Column("mfa_pending_secret_encrypted", sa.String(length=512), nullable=True)
    )
    op.add_column("users", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("mfa_last_used_step", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("mfa_recovery_code_hashes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "mfa_recovery_code_hashes")
    op.drop_column("users", "mfa_last_used_step")
    op.drop_column("users", "mfa_enabled_at")
    op.drop_column("users", "mfa_pending_secret_encrypted")
    op.drop_column("users", "mfa_secret_encrypted")
