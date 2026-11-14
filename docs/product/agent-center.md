# Agent Center

The Agent Center reports each specialist's real workspace workload, recent runs, success/failure evidence, provider availability, platform capabilities, and effective workspace configuration.

Workspace owners and administrators can activate or disable an agent and choose an approval policy. The API also supports a platform-bounded tool subset, execution action limit, monthly token budget, current-provider model preference, and workspace-owned knowledge source identifiers.

Configuration cannot expand an agent's platform tool allowlist. Disabled agents, unavailable model selections, exhausted budgets, and proposals outside the workspace tool subset are rejected server-side before an agent can create actions. The `always` approval policy escalates every proposed action to red risk; it cannot weaken platform approval rules.

Provider status is explicit:

- `operational`: a supported real provider is configured;
- `sandbox`: the fake provider is intentionally active;
- `unavailable`: required provider credentials are absent;
- `disabled`: the agent is disabled for the active workspace.

No secret or provider credential is returned to the browser.
