# CRM tenant migration

CRM currently repeats `user_id` across every table. The migration must preserve
creator/owner attribution while moving authorization to Workspace.

## Canonical roots

The following roots receive a required `workspace_id`:

- `crm_organizations`, `crm_contacts`, and `crm_tags`;
- `crm_clients`, `crm_pipelines`, and `crm_record_history`.

Projects, opportunities, task links, contact methods, addresses, notes, activities,
organization membership, tag links, and pipeline stages inherit tenant identity from
their required parent. Queries must join the parent root and compare it with the
authenticated user's active Workspace. This avoids contradictory duplicated tenant
columns while preserving object-level authorization.

## Migration invariants

- Backfill each root from its current user's `active_workspace_id` before adding
  non-null constraints.
- Replace user-scoped natural uniqueness with Workspace-scoped uniqueness.
- Validate that every cross-reference (`contact`, `organization`, `client`, `project`,
  `pipeline`, and `stage`) resolves inside the same Workspace.
- Keep `user_id` and `owner_user_id` as attribution/assignment fields only.
- Return not-found rather than forbidden for cross-tenant identifiers.
- Add PostgreSQL tests with two users in one Workspace and a third user in another,
  covering reads, writes, links, pipeline moves, history, and search.

The schema and repository changes must land together; adding tenant columns without
switching every query would create misleading partial isolation.
