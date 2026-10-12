# Marketing workspace

Operators can create tenant-scoped campaigns, move them through idea, active, paused,
completed, and archived states, and build content drafts inside each campaign. Content follows
an enforced lifecycle: draft → review → approved → scheduled. Returning to draft and archiving
remain explicit actions; an approved or scheduled item cannot be silently rewritten.

Scheduling only places approved content on the editorial calendar. Kiko does not publish to an
external channel. A publication becomes `published` only when an operator or governed tool
records a provider reference after the external action is confirmed.

Manual dashboard mutations require a workspace editor, admin, or owner and are audited as user
actions. Agent tool mutations retain exact-payload approval and worker attribution.
