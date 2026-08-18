# Action approvals

Kiko applies the most restrictive risk from the Task, proposed Action, registered Tool,
and server policy. A model can never lower Tool risk.

- green actions may queue automatically;
- yellow actions require user approval before the first execution;
- red actions require approval plus explicit high-risk confirmation.

When approval is requested, the server hashes the normalized tool name, version, sanitized
input payload, and effective risk. The `ApprovalRequest` stores this fingerprint. Before
queueing, approval locks both records and recalculates the hash. Any payload, version,
tool, or risk change invalidates the decision and requires a fresh approval.

The public API never allows a caller to impersonate Kiko, an agent, worker, or system.
Approval and action endpoints apply ownership through Task -> Plan -> Command and return
404 for another user's resources.

The dashboard exposes pending approvals at `/dashboard/approvals`. Red cards use a
strong warning and a required confirmation checkbox without preselection or dark patterns.
