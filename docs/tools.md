# Tool registry

`ToolRegistry` is the sole route from an approved action to executable code. The LLM
never calls handlers directly.

Every `ToolDefinition` declares name, version, description, allowed agent types, minimum
risk, timeout, retry budget, approval requirement, Pydantic input/output schemas, and a
handler. Unknown tools, unsupported versions, invalid schemas, and unauthorized agent
assignments are rejected before queueing.

Built-in Phase 3C tools:

| Tool                                | Risk   | Approval | Effect                                                         |
| ----------------------------------- | ------ | -------- | -------------------------------------------------------------- |
| `internal.echo`                     | green  | no       | Returns text                                                   |
| `internal.summarize`                | green  | no       | Uses the provider-neutral AI layer                             |
| `internal.create_note`              | green  | no       | Stores note content as the execution result linked to the Task |
| `internal.simulate_external_action` | yellow | yes      | Returns a simulated success only                               |
| `internal.simulate_critical_action` | red    | yes      | Returns a simulated success only                               |

No tool contacts Gmail, social platforms, GitHub, calendars, payments, CRM, websites, or
other external systems. Future tools must be registered with explicit schemas,
permissions, credentials, risk, idempotency, and recovery behavior.
