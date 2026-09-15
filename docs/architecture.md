# Agent architecture

## System overview

```text
Browser -> Next.js -> FastAPI route -> service -> repository -> PostgreSQL
                                      |
                                      +-> Redis rate limiter
                                      |
                                      +-> SupervisorService -> LLMProvider -> OpenAI

GET /ready -> readiness service -> PostgreSQL + Redis
```

The monorepo keeps HTTP contracts, use cases, storage operations, and infrastructure
separate. SQL never lives in routes and SQLAlchemy entities pass through Pydantic
schemas before public responses.

## Frontend

`apps/web` is a Next.js App Router application. `/login` and `/register` provide
accessible forms; `/dashboard` restores a session through refresh, retrieves `/me`,
shows the user and agent cards, and redirects to login when renewal fails. The command
area uses the same centralized authenticated client for lists, detail, manual planning,
task assignment, and explicit state transitions. The root redirects to `/dashboard`.
API failure affects status and authentication messages without preventing public pages
from rendering.

The centralized auth client sends cookies with `credentials: "include"`, retains its
access token only in module memory, retries an unauthorized request once, and shares a
single refresh promise among concurrent requests.

## Backend layers

- `api`: routing, dependencies, cookies, status codes, and response schemas;
- `services`: authentication use cases, transaction boundaries, readiness, and cleanup;
- `repositories`: SQLAlchemy statements without commits;
- `security`: Argon2id, JWT, opaque token generation, and token hashing;
- `db`: engine, session factory, declarative base, and infrastructure checks;
- `models`: internal SQLAlchemy entities;
- `schemas`: Pydantic request and public response contracts;
- `scripts`: explicit seed and cleanup commands;
- `core`: validated environment settings and UTC time helpers.

Repositories never decide HTTP responses. Services coordinate persistence and own each
commit or rollback. Routes translate domain errors into safe public errors.

## Command planning workflow

The persistent aggregate is `Command -> Plan[] -> Task -> TaskStatusHistory`. A command
belongs directly to a user. Versioned plans inherit ownership from their command; tasks
and history inherit it through the complete join path. Repository reads always include
that ownership path, so a guessed UUID from another account receives HTTP 404.

`CommandService`, `PlanService`, and `TaskService` coordinate validation and one
transaction for each mutation. Dedicated repositories contain the SQLAlchemy
statements. Status is excluded from generic task updates and changes only through the
state machine in `TaskService`. Every accepted transition and the initial
`null -> pending` event are appended to history with the acting user.

State mutations use pessimistic row locks. Task transitions and PATCH operations select
the owned task with `FOR UPDATE`; plan/task creation and command cancellation serialize
on the owning command. Validation, timestamp updates, history insertion, and commit stay
inside the same transaction, with explicit rollback on failure. Terminal commands cannot
receive additional plans or tasks. A partial unique index permits only one current plan
per command while preserving cancelled versions.

The Supervisor creates only draft/pending records. `RiskPolicy` raises obvious
under-classifications and approval is explicit. Risk remains descriptive because no
task execution exists yet. Shared TypeScript contracts mirror the public schemas.

## Authentication transactions

Registration creates the user and initial refresh token in one transaction. Login
updates `last_login_at` and creates its refresh token in one transaction. Refresh locks
the presented token, adds the replacement, revokes the predecessor, links
`replaced_by_id`, and commits once. Reuse revokes every active token in the family in
one update and commit. Repositories do not commit independently.

## PostgreSQL and Alembic

PostgreSQL is the system of record for agents, users, hashed refresh tokens, commands,
plans, tasks, and status history.
SQLAlchemy 2 uses typed `Mapped` fields, modern `select`/`update` statements, explicit
sessions, and timezone-aware timestamp columns with UTC application defaults.
Constructing the engine does not open a connection.

Alembic reads `DATABASE_URL` from the same settings. Revision `20260724_0001` creates
agents; `20260724_0002` independently creates users and refresh tokens with reversible
constraints, foreign keys, and indexes; `20260814_0003` creates the workflow tables,
enum checks, ownership links, ordering indexes, and a complete downgrade. Revision
`20260814_0004` evolves plans to one-to-many versioning and creates `supervisor_runs`.

## Supervisor and AI boundary

`SupervisorService` depends on the `LLMProvider` protocol, not the OpenAI SDK. The
OpenAI adapter uses structured output parsed directly into Pydantic schemas. Prompts
are code-versioned as `supervisor-plan-v1`, the agent catalog is loaded dynamically,
and provider metadata is persisted without raw prompts, raw responses, or API keys.

Generation uses two database transactions. The first locks the command, validates it,
creates a running `SupervisorRun`, sets `planning`, and commits. The external request
runs without a database lock. The second locks the command again, checks cancellation
and competing plans, then atomically writes the plan, ordered tasks, initial history,
and completed run. Failure marks the run failed and restores `pending` when no plan
exists. PostgreSQL locking plus uniqueness prevents duplicate current plans.

## Redis

Redis provides readiness and a deliberately small fixed-window limiter for register,
login, and refresh. Keys combine endpoint and a digest of the client IP. Development
defaults to fail-open if Redis is unavailable; production can select fail-closed with
`AUTH_RATE_LIMIT_FAIL_OPEN=false`. HTTP 429 includes `Retry-After`.

## Liveness, readiness, and startup

`/health` proves only that FastAPI is serving. `/ready` runs `SELECT 1` and `PING`,
reports each dependency, and returns 503 when needed without leaking details.

Compose waits for `postgres` and `redis`. The API entrypoint applies migrations, runs
the idempotent agent seed, and starts Uvicorn. Refresh-token cleanup remains an
explicit maintenance command rather than a startup or scheduled operation.

## Continuous integration

Backend and frontend jobs are independent. Backend uses Python 3.12, harmless test
settings, Ruff, Alembic offline SQL, SQLite-backed Pytest, and FakeGitHubClient. Frontend
uses Node 22, pnpm cache, ESLint, TypeScript, Vitest, and a production Next.js build. A
separate PostgreSQL 16 and Redis 7 job applies real migrations and exercises integration
locking/outbox behavior. CI requires no GitHub token or repository secret.

## Future orchestration

The Supervisor derives proposed plans and tasks; specialized agents turn ready tasks into
validated TaskActions. The Execution Engine remains the only route to handlers. Phase 5A
adds a narrowly scoped GitHub adapter for Development while authentication, credentials,
agent reasoning, persistence, and external transport remain separate layers.

| Agent           | Initial responsibility                                             |
| --------------- | ------------------------------------------------------------------ |
| **Supervisor**  | Prioritize work, delegate tasks, coordinate agents, track outcomes |
| **Marketing**   | Support campaigns, content, brand, and marketing operations        |
| **Sales**       | Support pipeline, proposals, outreach, and commercial follow-up    |
| **Support**     | Triage requests, organize knowledge, and assist customer service   |
| **Development** | Support delivery, technical planning, quality, and maintenance     |

## Execution architecture

The Execution Engine sits between proposed agent work and every handler:

```text
Kiko / Agent -> TaskAction -> risk and approval -> OutboxEvent
             -> Redis/Celery -> idempotent worker -> registered ToolHandler
             -> sanitized TaskExecution result -> workflow state propagation
```

PostgreSQL owns action, approval, attempt, outbox, dependency, and audit state. Celery
messages contain only execution identifiers. Tool handlers receive a constrained
`ExecutionContext` with user, command, task, action, execution, and correlation IDs.
They do not receive a universal service container or unrestricted credentials.

The system is deliberately at-least-once at the transport boundary and exactly-once at
the execution state boundary for completed attempts. Fingerprints bind human decisions to
the exact approved action. Audit rows are append-only and have no update/delete API.

## Specialized agent architecture

A versioned specialist prompt and bounded AgentTaskContext pass through the provider's
structured-output interface. AgentRunnerService records AgentRun before releasing locks,
then validates the returned proposal against the Agent Registry and Tool Registry. The
provider never sees secrets and never receives a callable tool. Proposed actions enter
the existing Execution Engine unchanged.

## GitHub integration boundary

```text
Development Agent -> schema-bound TaskAction -> repository/risk policy
                  -> approval for writes -> worker
                  -> CredentialProvider -> GitHubClient -> fixed GitHub API
```

The LLM sees tool names, schemas, and bounded task context but never a token, HTTP client,
arbitrary URL, or raw API response. The worker resolves credentials after it has locked
and validated the immutable action fingerprint. No database transaction remains open
during the external call. The handler validates the repository allowlist, path, branch,
protected-branch and size policies before delegating HTTP to `GitHubClient`.

Results are converted into explicit Pydantic output models, tagged as untrusted when they
contain external content, bounded before persistence, and sanitized again by the worker.
GitHub-specific audit events store identifiers and safe metadata only. The status API and
frontend expose configuration booleans and allowlisted repository names, never a
credential. CI substitutes an in-memory client and makes no GitHub network request.

## Codex execution boundary

```text
Development Agent -> schema-bound CodexTool -> approval for changes -> worker
                  -> CodexRunner -> isolated workspace -> CodexCLIAdapter
```

`CodexRun` is the persistent execution record and follows the action from approval through
queued, running, and terminal state. The CLI adapter uses `codex exec --ephemeral`, ignores
user configuration, selects read-only or workspace-write sandboxing, requires JSON Schema
output, uses `shell=False`, and deletes raw terminal logs. The runner—not the LLM—owns clone,
branch creation, fixed validation commands, one commit, and a non-force push. Credentials are
resolved only in the worker and are absent from schemas, prompts, persisted output, and the UI.
See [Codex integration](codex-integration.md).

## Email integration boundary

    Support/Sales -> EmailTool v2 -> approval for writes -> worker
                  -> EmailService -> SecretStore -> EmailProvider -> Gmail API

Per-user IntegrationAccount rows enforce ownership and store only encrypted refresh
credentials. EmailReference stores provider identifiers rather than mailbox copies;
EmailSendRecord provides action idempotency and delivery_unknown recovery. Plain text
normalization, attachment metadata, account/recipient policy and untrusted-content prompts
sit before agent consumption. CI substitutes FakeEmailProvider and needs no Google secret.
