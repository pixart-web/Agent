# Command, plan, and task workflow

Phase 3A introduced the persistent, authenticated control plane. Phase 3B adds a
provider-neutral Supervisor that proposes plans and ordered tasks for human review.
Transitions and execution remain explicit; generation never executes a task.

## Domain model

- A `Command` stores the user's instruction and belongs to exactly one user.
- A `Plan` describes the objective and belongs to a command with a unique version.
  Only one plan can be current; rejected or superseded versions remain auditable.
- A `Task` belongs to a plan, references an existing agent, and records ordering,
  priority, risk, execution timestamps, and an optional failure message.
- `TaskStatusHistory` is append-only audit data for the initial state and every accepted
  transition. It records the acting user and an optional reason.

Commands use `pending`, `planning`, `in_progress`, `completed`, `failed`, or
`cancelled`. Plans use `draft`, `ready`, `in_progress`, `completed`, `failed`, or
`cancelled`. Generation creates plans as draft and tasks as pending. Approval
atomically changes the plan and tasks to ready and the command to in progress.
Replanning cancels only the current draft and creates the next version.

## Task state machine

Only the dedicated transition endpoint can change task status. Generic PATCH requests
may update assignment, content, priority, risk, or sequence, but reject `status`.

```text
pending ----------> ready ----------> running ----------> completed
   |                  |  |              |  |  |
   |                  |  +-> blocked ---+  |  +-> failed ----+
   |                  |                    +-> waiting_approval |
   |                  |                          |               |
   +-> cancelled <----+--------------------------+---------------+
                              retry to ready <----
```

The exact allowed transitions are:

| From               | To                                                   |
| ------------------ | ---------------------------------------------------- |
| `pending`          | `ready`, `cancelled`                                 |
| `ready`            | `running`, `cancelled`, `blocked`                    |
| `running`          | `completed`, `failed`, `waiting_approval`, `blocked` |
| `waiting_approval` | `ready`, `cancelled`                                 |
| `blocked`          | `ready`, `cancelled`                                 |
| `failed`           | `ready`, `cancelled`                                 |
| `completed`        | terminal                                             |
| `cancelled`        | terminal                                             |

An invalid transition returns HTTP 409. Entering `running` sets `started_at` the first
time. Entering `completed`, `failed`, or `cancelled` sets `completed_at`. Retrying from
`failed` to `ready` clears `completed_at` and `error_message`.

## Priority and risk

Priorities are `low`, `normal`, `high`, and `urgent`. Risk levels are `green`, `yellow`,
and `red`. They are operator metadata in this phase: they do not bypass ownership,
automatically approve work, or start execution.

## Ownership and transactions

Every endpoint requires authentication. Commands are filtered by the authenticated
user. Plans, tasks, and history resolve ownership through `Plan -> Command -> User`.
The API does not trust IDs supplied by the browser and returns HTTP 404 for foreign
resources to avoid confirming that they exist. Agent IDs are validated against the
persistent catalog before task creation.

Mutations follow `route -> service -> repository -> database`. Routes contain no SQL;
repositories never commit; services own the transaction. Task creation writes the task
and its `null -> pending` history record atomically. A transition changes timestamps
and appends history in the same transaction.

Task transitions acquire a PostgreSQL row lock with `SELECT ... FOR UPDATE OF tasks`
before reading the current state. The lock remains held while the service validates the
transition, changes timestamps, appends history, and commits. Concurrent transitions on
the same task therefore serialize and the second transaction validates against the
newly committed state. Task PATCH uses the same locked read to avoid lost updates.

Plan creation and task creation lock the owning command while checking its lifecycle.
Commands in `completed`, `failed`, or `cancelled` cannot receive new plans or tasks and
return HTTP 409. Command cancellation takes the same command lock, preventing a race
between cancellation and adding more work.

SQLite ignores `FOR UPDATE`, so the isolated test suite cannot reproduce PostgreSQL
row-lock scheduling. Tests instead compile the repository statement with the PostgreSQL
dialect, verify that mutation services use the locked path, and assert rollback and
history invariants. Real contention behavior remains a PostgreSQL integration concern.

## API and frontend flow

The command list supports `limit`, `offset`, and an optional `status` filter, with a
maximum page size of 100. Task detail includes ordered history.

The protected pages are:

- `/dashboard/commands` — owned commands, status, date, and task progress;
- `/dashboard/commands/new` — capture a new operational instruction;
- `/dashboard/commands/{id}` — create the plan and tasks, assign agents, inspect risk,
  apply valid transitions, cancel the command, and expand history.

The workflow client uses the existing in-memory access token and synchronized refresh
flow. It never stores tokens in browser storage. API errors are presented without
internal exceptions or database details.

## Supervisor flow

The Supervisor receives the original command, the active agent catalog, and — during
replanning — a bounded summary plus user feedback. Its structured proposal is checked
for sizes, sequences, valid agents, critical assignments, and minimum risk before an
atomic write. The provider call occurs between two short transactions, so PostgreSQL
locks are not held during network latency. See `docs/supervisor.md` for failure and
concurrency behavior. Background workers, artifacts, and execution remain out of scope.
