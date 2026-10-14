# Marketing tenant migration

Migration `20261010_0023` makes `marketing_campaigns` the workspace-scoped root
for the complete Marketing aggregate. Content, assets, publications, performance
metrics, and lifecycle history inherit tenant identity through their campaign or
content foreign keys; `user_id` remains actor attribution rather than authorization.

## Invariants

- Every persisted campaign has a non-null `workspace_id` after migration.
- Campaign reads and writes resolve against the authenticated user's active workspace.
- Content and all descendants are accessed only after joining to or validating their
  campaign root.
- A client attached to a campaign must belong to the same active workspace.
- A task attached to content must belong to the same active workspace.
- Cross-workspace identifiers return not-found and never disclose existence.
- External publication remains confirmation-only; Kiko does not claim unsupported
  provider publishing.

## Migration and rollback

Existing campaigns are backfilled from each creator's active workspace before the
column becomes non-null. Tenant-oriented indexes replace user-oriented indexes for
campaign lists, content lifecycle/calendar queries, metrics, and history. The
downgrade restores the former indexes and removes the workspace foreign key and
column without deleting campaign data.

The nullable ORM field and `workspace_or_legacy_owner` branch support only unmigrated
test/legacy rows. Production schema revision `20261010_0023` disallows null tenants.
