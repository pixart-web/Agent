# Approval Center

The Approval Center is the workspace control surface for consequential actions. Every card is backed by a fingerprinted `TaskAction`, not a UI-only proposal.

It exposes the requesting agent, related task, target integration, tool, exact sanitized payload, risk, expected impact description, request and expiry times, discussion, and an immutable audit-derived event history. Users may inspect pending and decided requests, comment, approve, or reject.

Requests expire after `APPROVAL_EXPIRE_HOURS` (24 hours by default). Lazy reconciliation on approval reads marks overdue requests expired, restores the action to `proposed`, and returns the task to `ready`, allowing a new fingerprinted request. An expired request can never be approved.

Red-risk approval requires explicit confirmation. When a workspace has more than one member, the requester cannot approve their own red-risk request; a different authorized workspace member must decide it. Single-member workspaces retain an explicit-confirmation path so they are not permanently deadlocked. Rejection remains available to the requester.

Comments are tenant-scoped, persisted, length-limited, and recorded in the approval audit trail. Fingerprint verification still runs inside the locked approval transaction immediately before queueing.
