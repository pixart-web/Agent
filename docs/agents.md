# Specialized agents

Phase 4 introduces Marketing, Sales, Support, and Development specialists. The Supervisor
assigns Tasks; a specialist analyzes one ready Task and returns a structured
`AgentProposal`. Only the Execution Engine can dispatch or execute the resulting
`TaskAction` rows.

`AgentRunnerService` uses two short transactions around the provider call. The first
locks and validates the owned Task and creates an active `AgentRun`; the second validates
tool names, versions, schemas, allowlists, ordering and effective risk before persisting
actions. No database lock is held during LLM latency.

Context is bounded and excludes secrets. Task instructions are untrusted input. Prompts
forbid prompt disclosure, direct execution, invented tools, policy overrides and lowered
risk. PostgreSQL's partial unique index prevents two active runs for the same Task.

Endpoints provide run/rerun, run history, capabilities, agent overview metrics, and
explicit safe reassignment. Re-runs preserve history and require a failed run, reset
actions, or user feedback.
