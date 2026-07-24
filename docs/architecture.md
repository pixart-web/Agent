# Agent architecture

## System overview

Agent is a modular monorepo with a browser dashboard, a versioned HTTP API, PostgreSQL
persistence, and Redis readiness. The current domain is deliberately small: it stores
the five initial agent definitions while preserving boundaries needed for later
orchestration.

```text
Browser
   |
   v
Next.js web
   |
   v
FastAPI route
   |
   v
Service
   |
   v
Repository -> SQLAlchemy session -> PostgreSQL

Readiness service -----------------------> Redis
```

## Frontend

`apps/web` contains a Next.js App Router application written in TypeScript. The
dashboard displays the initial agent team and probes `/health` to communicate whether
the API process is online. A failed probe changes only the status indicator; the rest
of the interface continues to render.

`NEXT_PUBLIC_API_URL` defines the API base URL.

## Backend

`apps/api` contains the FastAPI service. Responsibilities are separated as follows:

- `api`: HTTP routing, dependency injection, status codes, and response schemas;
- `services`: use-case decisions and not-found behavior;
- `repositories`: SQLAlchemy statements and persistence operations;
- `db`: engine, session factory, declarative base, and infrastructure checks;
- `models`: internal SQLAlchemy entities;
- `schemas`: validated Pydantic API contracts;
- `scripts`: explicit maintenance commands such as the initial seed;
- `core`: environment-based application settings.

Routes never contain SQL. SQLAlchemy entities are converted through Pydantic schemas
before they become API responses.

## PostgreSQL and SQLAlchemy

PostgreSQL is the system of record. SQLAlchemy 2 uses typed `Mapped` fields, modern
`select` statements, and explicit sessions. Constructing the engine does not open a
connection; connections are acquired only by requests, migrations, seeds, or readiness
checks.

`get_db` provides one session per request and closes it at the end of the dependency
scope. Agent timestamps use timezone-aware columns and UTC application defaults.

## Alembic

Alembic lives in `apps/api/alembic`. Its environment imports the declarative metadata
and reads `DATABASE_URL` from the same settings object as the API. Migrations remain
explicit and reversible.

The initial revision creates the `agents` table with identity, descriptive fields,
status, and UTC-capable timestamps.

## Seed

`python -m app.scripts.seed_agents` runs an explicit, idempotent seed. The repository
inserts missing initial agents and updates only `name`, `description`, and `status`
when their managed definitions change.

The seed is not executed by requests. Docker runs it once during each API container
startup after applying migrations; idempotency makes retries safe.

## Redis

Redis is currently checked by `/ready` and reserved for future caching, distributed
coordination, rate limiting, and queues. No queue framework is selected yet.

## Liveness and readiness

- `/health` is a liveness endpoint. It proves that FastAPI can serve requests without
  contacting dependencies.
- `/ready` checks PostgreSQL with `SELECT 1` and Redis with `PING`. It returns HTTP 503
  if either dependency is unavailable and reports each service independently.

Errors are reduced to `healthy` or `unavailable`; connection strings, credentials, and
stack traces are never included.

## Docker startup

Compose requires the `postgres` and `redis` containers to become healthy before
starting the API. The API entrypoint then:

1. runs `alembic upgrade head`;
2. runs the idempotent seed;
3. replaces itself with the Uvicorn process.

The internal hostnames are `postgres` and `redis`.

## Continuous integration

`.github/workflows/ci.yml` contains independent backend and frontend jobs:

- Python 3.12, dependency installation, Ruff, Alembic offline validation, and Pytest;
- Node.js 22, Corepack/pnpm, dependency cache, ESLint, TypeScript, and Next.js build.

Tests use SQLite in memory and FastAPI dependency overrides, so CI requires no
PostgreSQL, Redis, or secrets.

## Future multi-agent orchestration

A later orchestration layer will receive tasks, ask the Supervisor to plan and delegate
work, execute specialized capabilities, persist state, and expose progress to the
dashboard. Agent definitions remain separate from model providers and tools so those
concerns can evolve independently.

## Initial agent responsibilities

| Agent           | Initial responsibility                                             |
| --------------- | ------------------------------------------------------------------ |
| **Supervisor**  | Prioritize work, delegate tasks, coordinate agents, track outcomes |
| **Marketing**   | Support campaigns, content, brand, and marketing operations        |
| **Sales**       | Support pipeline, proposals, outreach, and commercial follow-up    |
| **Support**     | Triage requests, organize knowledge, and assist customer service   |
| **Development** | Support delivery, technical planning, quality, and maintenance     |
