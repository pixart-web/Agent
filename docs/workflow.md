# Command, plan, and task workflow

Phase 3A introduces the persistent, authenticated control plane for Agent. A user can
record an operational instruction, describe its plan, assign ordered tasks to the five
configured agents, and audit every status change. Planning and transitions are manual;
there is no OpenAI call or automatic execution.

## Domain model

- A `Command` stores the user's instruction and belongs to exactly one user.
- A `Plan` describes the objective and has a unique foreign key to one command.
- A `Task` belongs to a plan, references an existing agent, and records ordering,
  priority, risk, execution timestamps, and an optional failure message.
- `TaskStatusHistory` is append-only audit data for the initial state and every accepted
  transition. It records the acting user and an optional reason.

Commands use `pending`, `planning`, `in_progress`, `completed`, `failed`, or
`cancelled`. Plans use `draft`, `ready`, `in_progress`, `completed`, `failed`, or
`cancelled`. This phase creates commands as pending, plans as draft, and tasks as
pending. Command cancellation is explicit; plan and task automation is reserved for
the Supervisor.

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

## Future Supervisor flow

In a later subphase, the Supervisor will turn a command into a proposed plan and task
graph, apply risk and approval policies, and delegate executable tasks. Background
workers, model calls, artifacts, and automatic state progression remain intentionally
out of scope for 3A.
