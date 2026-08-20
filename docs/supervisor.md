# Supervisor planning

Phase 3B turns a user-owned command into a proposed plan without executing work.

```text
Command -> SupervisorService -> LLMProvider -> structured proposal
   |                                             |
   +-> SupervisorRun <- validation <- RiskPolicy+
   |
   +-> Plan version -> ordered Tasks -> human approval
```

## Generation and transactions

The service uses two explicit transactions. Transaction 1 locks the command, validates
ownership and lifecycle, prevents an active duplicate run, creates a running
`SupervisorRun`, changes the command to `planning`, and commits. The provider call then
runs without an open database transaction. Transaction 2 locks the command and run,
rechecks cancellation/current-plan invariants, and atomically persists the draft plan,
pending tasks, initial history, usage metadata, and completed run.

Provider or validation failure creates no partial plan. The run becomes `failed`, and a
command without a current plan returns to `pending`. A cancellation observed after the
provider response marks the run `cancelled` and discards the proposal. PostgreSQL row
locks and the partial current-plan uniqueness index form the concurrency boundary.
SQLite ignores `FOR UPDATE`, so deterministic tests cover the locked repository/service
path and the active-run/uniqueness invariants; true lock scheduling remains a PostgreSQL
integration concern.

## Structured proposal and guardrails

The `supervisor-plan-v1` system prompt supplies the dynamic active agent catalog,
priority/risk meanings, maximum task count, planning-only boundary, and untrusted-input
rules. The command is delimited as user data. Only a short `reasoning_summary` is
requested and stored; chain-of-thought, raw prompts, and raw provider responses are not.

Pydantic and domain policies validate title/instruction sizes, positive unique
sequences, task count, enums, active agent IDs, and a few critical assignment rules.
`RiskPolicy` raises obvious payment, destructive, legal, credential, and production
actions to red, and external communications/changes to at least yellow. These are
defense-in-depth controls; prompt injection is not considered solved.

## Review, versions, and endpoints

- `POST /api/v1/commands/{id}/generate-plan` creates v1 or the next version when no
  current plan exists.
- `POST /api/v1/commands/{id}/regenerate-plan` supersedes a current draft with bounded
  feedback and creates the next version.
- `GET /api/v1/commands/{id}/supervisor-runs` exposes safe status and usage metadata.
- `GET /api/v1/commands/{id}/plans` and `GET /api/v1/plans/{id}` expose history.
- `POST /api/v1/plans/{id}/approve` changes draft/pending records to ready and the
  command to in progress in one transaction.
- `POST /api/v1/plans/{id}/reject` cancels the draft and pending tasks, preserves the
  reason, and returns the command to pending.

The dashboard disables duplicate clicks, shows a planning state, task assignment,
priority, risk, model, tokens and latency, then offers approval or feedback-driven
replanning. It also warns users not to include passwords, API keys, or other secrets.

## Limits and privacy

`SUPERVISOR_MAX_COMMAND_CHARS`, `SUPERVISOR_MAX_FEEDBACK_CHARS`, and
`SUPERVISOR_MAX_TASKS` bound provider input/output. Commands and feedback are sent to
the configured provider; users should not submit secrets. Logs contain only run and
command IDs, provider/model, latency, tokens, and safe error codes. API keys, prompts,
cookies, full provider responses, and raw command content are excluded.

No background job, tool call, or automatic task execution exists in Phase 3B.
