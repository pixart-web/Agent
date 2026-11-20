"""Drop unique constraints duplicated by unique indexes (KQA-010).

`account_tokens.token_hash` and `workspaces.slug` had both a unique constraint and a unique
index; `codex_runs.task_action_id` had a unique constraint plus a plain index. Each column
keeps exactly one unique index, which is what the ORM models declare, so `alembic check`
reports no differences.
"""

from alembic import op

revision = "20261120_0036"
down_revision = "20261014_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("account_tokens_token_hash_key", "account_tokens", type_="unique")
    op.drop_constraint("workspaces_slug_key", "workspaces", type_="unique")
    # Create the unique index before dropping the constraint, so uniqueness never lapses.
    op.drop_index("ix_codex_runs_task_action_id", table_name="codex_runs")
    op.create_index("ix_codex_runs_task_action_id", "codex_runs", ["task_action_id"], unique=True)
    op.drop_constraint("codex_runs_task_action_id_key", "codex_runs", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("codex_runs_task_action_id_key", "codex_runs", ["task_action_id"])
    op.drop_index("ix_codex_runs_task_action_id", table_name="codex_runs")
    op.create_index("ix_codex_runs_task_action_id", "codex_runs", ["task_action_id"])
    op.create_unique_constraint("workspaces_slug_key", "workspaces", ["slug"])
    op.create_unique_constraint("account_tokens_token_hash_key", "account_tokens", ["token_hash"])
