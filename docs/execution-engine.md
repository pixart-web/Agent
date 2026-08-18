# Kiko execution engine

Phase 3C introduces a generic, auditable execution path without connecting real external
services.

```text
Task ready -> TaskAction -> policy -> approval -> TaskExecution
           -> transactional outbox -> Celery -> worker -> validated result
```

## Source of truth and transactions

PostgreSQL is the only source of truth. Redis and Celery transport execution IDs; Celery
results are ignored. Queue intent is written as an `OutboxEvent` in the same transaction
that marks an action queued. The dispatcher claims events with `FOR UPDATE SKIP LOCKED`,
publishes them, and records delivery. Duplicate delivery is safe because the worker locks
`TaskExecution` and treats terminal or already-running attempts as no-ops.

The worker uses three phases:

1. lock and claim execution/action/task, then commit;
2. execute the registered handler without an open database transaction;
3. lock again and atomically persist a sanitized result or failure.

The first running task advances Plan and Command to `in_progress`. A task completes only
when every non-cancelled action completes. All tasks completed advances Plan and Command
to `completed`; an exhausted mandatory action fails Task, Plan, and Command.

## Retries and recovery

Tools declare their retry budget. `RetryPolicy` applies the lower of tool and system
limits with exponential backoff and jitter. Every retry is a new immutable
`TaskExecution` attempt and a future outbox event. Validation and permission failures
are not retryable.

Celery applies each tool's soft and hard time limits. Run
`python -m app.scripts.recover_stale_executions` to mark abandoned running attempts for
manual review. Future non-idempotent tools must define a recovery policy before automatic
replay.

## Cancellation

Command cancellation transactionally cancels unfinished plans, non-running tasks,
unstarted actions, queued attempts, and pending approvals. Running handlers are not
force-killed in this phase; cancellation is best effort and late results cannot revive a
cancelled Command.

## Security

Only registered tool names and versions execute. Inputs and outputs pass through
`sanitize_execution_payload`; common password, token, cookie, credential, API-key, and
secret fields are replaced with `[REDACTED]`. Logs and audits contain identifiers and
safe metadata, not full payloads or stack traces.

## Specialized-agent boundary

AgentRun produces only proposed TaskActions. Green, yellow and red proposals follow the
same dispatch, approval, outbox and worker path as manually created actions. The agent
cannot enqueue Celery, invoke a handler, lower tool risk, or bypass an approval.
