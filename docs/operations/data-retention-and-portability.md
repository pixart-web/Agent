# Data retention and portability

## Scope

Workspace owners and administrators can export explicitly allowlisted business
records from **Settings → Data portability**. JSON archives contain the workspace
profile, contacts, organizations, projects, tasks, and activities. A CSV export is
available for one resource at a time. Exports are bounded to 10,000 rows per
resource and produce an audit event.

Authentication records, password hashes, sessions, invitation tokens, OAuth
tokens, provider credentials, integration secrets, and raw provider payloads are
never included. The export is generated only for the caller's active workspace.

## Retention policy

Each workspace has a configurable policy between 30 and 3,650 days. The policy
applies automatically only to transient records that are no longer operational:

- read in-app notifications older than the cutoff;
- revoked or expired invitations older than the cutoff.

Unread notifications, audit logs, commands and execution history, CRM records,
projects, tasks, knowledge documents, integration references, and commercial
records are preserved. Their deletion requires a separately reviewed lifecycle
operation; changing `retention_days` must not silently remove business evidence.

Only a workspace owner can preview or execute retention. Execution requires the
exact confirmation `DELETE_EXPIRED_TRANSIENT_DATA`, is tenant-scoped, and records
the cutoff, deletion counts, actor, and correlation ID in the audit trail.

## Backup interaction

Retention operates on the live database and does not rewrite existing backup
snapshots. Backup expiry is controlled by the infrastructure backup schedule.
Consequently, deleted transient data may remain in encrypted backups until those
snapshots expire. A restore can temporarily reintroduce records that were eligible
for retention; operators must run a retention preview and execution after a
restore before returning the environment to service.

Before a workspace closure or a broader data-erasure operation, operators must:

1. offer an authorized export;
2. identify legal/audit preservation requirements;
3. take and verify the required recovery point;
4. execute only an approved, workspace-specific deletion procedure;
5. record the action and its backup-expiry implications.

No application endpoint deletes backup snapshots, and no production retention
operation is run as part of a software deployment.
