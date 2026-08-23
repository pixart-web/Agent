# External integrations

Kiko integrations are adapters behind the existing Execution Engine. An agent can only
propose a registered, schema-bound TaskAction. The agent and LLM never receive a network
client or credential.

```text
Agent -> TaskAction -> Tool Registry -> Risk Policy -> Approval
      -> Outbox -> Worker -> Credential Provider -> Integration Client
```

Credentials are resolved by the worker immediately before handler execution. They are
not accepted by tool input schemas, persisted with TaskAction or TaskExecution, returned
to the frontend, or included in audit metadata. Environment-backed configuration is the
initial provider; the abstraction permits a managed secret store later.

Every integration must define:

- an explicit repository or resource allowlist;
- Pydantic input and output schemas with `extra=forbid`;
- minimum risk and approval requirements;
- bounded timeouts, output sizes, and retry behavior;
- typed safe errors and sanitized audit metadata;
- an in-memory fake for deterministic CI;
- a policy for untrusted external content and idempotent writes.

GitHub is the first real integration. No direct integration endpoint performs GitHub
operations; the only administrative API returns safe configuration status.

## Codex

Codex is an execution integration rather than a general-purpose agent tool. Development
proposes a bounded specification; the Execution Engine applies risk and approval; a dedicated
worker resolves credentials and invokes the CLI in an isolated workspace. Configuration and
safe run status are visible at `/dashboard/codex`, while terminal output and secrets never are.
See [Codex integration](codex-integration.md).
