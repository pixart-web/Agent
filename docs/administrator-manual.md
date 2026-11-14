# Administrator manual

Workspace Owners control ownership, lifecycle, retention, billing records, integrations, and data
exports. Admins manage most workspace resources and members. Managers coordinate operational work;
Members contribute; Viewers are read-only. Platform administration is distinct from workspace
administration and must use separately assigned platform roles.

Before inviting users, confirm their exact email and least-privilege role. Invitations expire, are
email-bound, can be revoked, and never grant access to another workspace. Keep at least two trusted
Owners before transferring ownership. Suspend a workspace before closure and preserve required audit
or legal records.

Enable one integration at a time. Use provider-specific test accounts, minimum scopes, explicit
repository/recipient/calendar allowlists, and verify the callback plus reconciliation result. Keep
external writes behind approval. Rotate credentials through the secret manager; never paste them
into Kiko conversations or repository files.

Review activity, failed executions, stale approvals, automation failures, entitlements, notification
delivery, storage, and backup age. Export uses explicit resource allowlists. Retention execution
requires Owner access and exact confirmation and intentionally preserves business and audit records.
Follow the staging and production runbooks for every release.
