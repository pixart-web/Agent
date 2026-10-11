# Command lifecycle

Commands are workspace-scoped operational requests. Their plans, tasks, executions, approvals, and audit evidence remain intact when a command is archived or duplicated.

## Search and visibility

- `GET /api/v1/commands?search=...` performs a bounded, case-insensitive search over command input.
- Active commands are returned by default.
- `include_archived=true` includes archived commands without changing their operational state.
- Status, limit, and offset filters remain compatible with the existing API.

## Archive and restore

- Only terminal commands (`completed`, `failed`, or `cancelled`) can be archived.
- Archiving is reversible and only changes list visibility; it never removes workflow or audit records.
- `POST /api/v1/commands/{id}/archive` archives a terminal command.
- `POST /api/v1/commands/{id}/restore` restores it to active lists.

## Duplicate

- `POST /api/v1/commands/{id}/duplicate` creates a new pending command in the active workspace.
- The new command copies only the operational input and stores `duplicated_from_id` for provenance.
- Plans, tasks, approvals, executions, conversations, and external side effects are never copied.

All lifecycle actions resolve the source command inside the caller's active workspace. Cross-workspace identifiers return `404`.
