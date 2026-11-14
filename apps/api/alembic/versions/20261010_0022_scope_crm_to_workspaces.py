"""Scope CRM aggregate roots to workspaces.

Revision ID: 20261010_0022
Revises: 20261010_0021
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0022"
down_revision: str | None = "20261010_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROOT_TABLES = (
    "crm_organizations",
    "crm_contacts",
    "crm_tags",
    "crm_clients",
    "crm_pipelines",
    "crm_record_history",
)


def upgrade() -> None:
    for table in ROOT_TABLES:
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

    op.drop_index("ix_crm_organizations_owner_name", table_name="crm_organizations")
    op.create_index(
        "ix_crm_organizations_workspace_name",
        "crm_organizations",
        ["workspace_id", "normalized_name"],
    )
    op.drop_index("ix_crm_contacts_owner_name", table_name="crm_contacts")
    op.create_index(
        "ix_crm_contacts_workspace_name",
        "crm_contacts",
        ["workspace_id", "normalized_name"],
    )
    op.drop_constraint("uq_crm_tag_owner_name", "crm_tags", type_="unique")
    op.create_unique_constraint(
        "uq_crm_tag_workspace_name", "crm_tags", ["workspace_id", "normalized_name"]
    )
    op.drop_constraint("uq_crm_client_owner_organization", "crm_clients", type_="unique")
    op.create_unique_constraint(
        "uq_crm_client_workspace_organization",
        "crm_clients",
        ["workspace_id", "organization_id"],
    )
    op.drop_constraint("uq_crm_pipeline_owner_name", "crm_pipelines", type_="unique")
    op.create_unique_constraint(
        "uq_crm_pipeline_workspace_name", "crm_pipelines", ["workspace_id", "name"]
    )
    op.drop_index("ix_crm_record_history_owner_entity", table_name="crm_record_history")
    op.create_index(
        "ix_crm_record_history_workspace_entity",
        "crm_record_history",
        ["workspace_id", "entity_type", "entity_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_record_history_workspace_entity", table_name="crm_record_history")
    op.create_index(
        "ix_crm_record_history_owner_entity",
        "crm_record_history",
        ["user_id", "entity_type", "entity_id", "created_at"],
    )
    op.drop_constraint("uq_crm_pipeline_workspace_name", "crm_pipelines", type_="unique")
    op.create_unique_constraint("uq_crm_pipeline_owner_name", "crm_pipelines", ["user_id", "name"])
    op.drop_constraint("uq_crm_client_workspace_organization", "crm_clients", type_="unique")
    op.create_unique_constraint(
        "uq_crm_client_owner_organization", "crm_clients", ["user_id", "organization_id"]
    )
    op.drop_constraint("uq_crm_tag_workspace_name", "crm_tags", type_="unique")
    op.create_unique_constraint("uq_crm_tag_owner_name", "crm_tags", ["user_id", "normalized_name"])
    op.drop_index("ix_crm_contacts_workspace_name", table_name="crm_contacts")
    op.create_index("ix_crm_contacts_owner_name", "crm_contacts", ["user_id", "normalized_name"])
    op.drop_index("ix_crm_organizations_workspace_name", table_name="crm_organizations")
    op.create_index(
        "ix_crm_organizations_owner_name",
        "crm_organizations",
        ["user_id", "normalized_name"],
    )

    for table in reversed(ROOT_TABLES):
        op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        op.drop_constraint(f"fk_{table}_workspace_id", table, type_="foreignkey")
        op.drop_column(table, "workspace_id")
