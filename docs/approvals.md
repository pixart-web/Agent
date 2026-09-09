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

## Codex change approvals

`codex.implement_task` and `codex.fix_pull_request` are always yellow. The approval preview
names the repository and target branch or PR and states that the runner may edit approved
paths, run its fixed validation profile, create one commit, and push. It also states the hard
limits: no merge, deployment, secrets, force push, or primary/production branch. The action
fingerprint binds that approval to the exact payload. `codex.review_pull_request` is green
because it is read-only and cannot publish a review.

## Email approvals

Email send, reply, and mark-read tools are yellow. The approval displays the selected
account, complete recipients, subject, full body, and a side-effect warning. Approval and
execution verify the same action fingerprint. A timed-out write becomes delivery_unknown
and is never retried blindly.
