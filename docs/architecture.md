# Agent architecture

## System overview

```text
Browser -> Next.js -> FastAPI route -> service -> repository -> PostgreSQL
                                      |
                                      +-> Redis rate limiter

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

The persistent aggregate is `Command -> Plan -> Task -> TaskStatusHistory`. A command
belongs directly to a user. A plan inherits ownership from its unique command; tasks
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
receive additional plans or tasks.

Risk is descriptive in 3A: green, yellow, and red are visible to operators but do not
yet trigger execution or approval automation. Shared TypeScript contracts mirror the
public schemas and transition map used by the UI.

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
enum checks, ownership links, ordering indexes, and a complete downgrade.

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

Backend and frontend jobs are independent. Backend uses Python 3.12, explicit harmless
test settings, Ruff, Alembic offline SQL, and SQLite-backed Pytest. Frontend uses Node
22, pnpm cache, ESLint, TypeScript, Vitest, and a production Next.js build. CI requires
no service containers or secrets.

## Future orchestration

A later Supervisor layer will derive plans and tasks from commands, delegate them,
invoke specialized capabilities, and produce artifacts. Phase 3A persists the manual
control plane and audit trail only: it performs no model call and executes no task.
Authentication is kept separate from agent execution so both can evolve independently.

| Agent           | Initial responsibility                                             |
| --------------- | ------------------------------------------------------------------ |
| **Supervisor**  | Prioritize work, delegate tasks, coordinate agents, track outcomes |
| **Marketing**   | Support campaigns, content, brand, and marketing operations        |
| **Sales**       | Support pipeline, proposals, outreach, and commercial follow-up    |
| **Support**     | Triage requests, organize knowledge, and assist customer service   |
| **Development** | Support delivery, technical planning, quality, and maintenance     |
