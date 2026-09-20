# Workspaces and business knowledge

Phase 9 introduces workspace-scoped, provenance-aware business knowledge. It does not
retrofit the earlier user-owned CRM and workflow tables; that remains a staged migration so
existing records do not acquire ambiguous tenant ownership.

## Authorization boundary

- `owner`: manages members, drafts and approvals, including restricted items.
- `admin`: manages members, drafts and approvals, including restricted items.
- `member`: creates and edits only their own drafts; reads approved internal/confidential data.
- `viewer`: reads approved internal data only.

Every service query includes `workspace_id` and a verified membership. A non-member receives
the same generic not-found result as an unknown workspace. Retrieval never returns drafts,
archived items or restricted items to member/viewer roles. Client and project references must
also belong to the authenticated user's existing CRM scope.

Knowledge content and provenance are untrusted reference data. They are never treated as
system instructions. Agent access is a read-only, GREEN `knowledge.search` tool backed by the
same authorization service; mutations remain authenticated operator actions and approval is
restricted to owners/admins.

## Retrieval decision

PostgreSQL full-text search was selected for this stage. The corpus is structured, tenant
filters are mandatory and exact provenance is more important than approximate semantic
matching. A GIN index supports ranked full-text results. SQLite uses a deterministic substring
fallback only for local tests.

`pgvector` and an external vector database were deliberately not added. A future hybrid
retriever can add embeddings once measured recall on a representative corpus justifies the
operational cost. It must retain relational authorization filters before ranking.

## Synthetic demo

Create the explicitly fictional dataset for an existing user:

```bash
python -m app.scripts.seed_sporting_demo_knowledge --user-email operator@example.com
```

All records state that they are synthetic and have no Sporting Clube de Portugal affiliation.
The test suite verifies that the prompt “Prepare a sponsor campaign consistent with Sporting
Demo brand rules” retrieves only approved, relevant records from the authorized workspace.
