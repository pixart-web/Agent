# Kiko — Pixart AI Operating System

Kiko is Pixart's AI operating system. This monorepo provides a Next.js
dashboard, a FastAPI API, PostgreSQL persistence, Redis infrastructure, secure user
authentication, migrations, continuous integration, and an AI-assisted Supervisor.
Authenticated users can turn an operational command into a structured, versioned plan,
review its assigned tasks, approve it, request revisions, and run safe registered internal
tools through an audited Execution Engine. Real external-service integrations remain
deliberately out of scope.

## Architecture

- **Web:** Next.js 15 App Router, React, and TypeScript.
- **API:** FastAPI on Python 3.12.
- **Persistence:** SQLAlchemy 2 with explicit sessions and PostgreSQL.
- **Authentication:** Argon2id passwords, short JWT access tokens, and rotating opaque
  refresh tokens in HttpOnly cookies.
- **Workflow:** owned commands, versioned plans, agent tasks, immutable status history,
  and explicit human approval.
- **AI:** provider-neutral structured generation with an initial OpenAI Responses API
  adapter, domain validation, and audited Supervisor runs.
- **Infrastructure:** Redis for readiness and authentication rate limiting.
- **Migrations:** Alembic configured from application settings.
- **Local environment:** Docker Compose for web, API, PostgreSQL, and Redis.
- **CI:** independent backend and frontend jobs in GitHub Actions.

Domain requests follow:

```text
HTTP route -> service -> repository -> SQLAlchemy session -> PostgreSQL
```

Authentication details are in [docs/authentication.md](docs/authentication.md);
workflow rules are in [docs/workflow.md](docs/workflow.md); Supervisor behavior is in
[docs/supervisor.md](docs/supervisor.md); provider setup is in
[docs/ai-providers.md](docs/ai-providers.md); system boundaries are in
[docs/architecture.md](docs/architecture.md).

## Requirements

With Docker: Docker Engine/Desktop and Compose v2. Make is optional. Without Docker:
Node.js 22+, pnpm 11+, Python 3.12+, PostgreSQL 16+, and Redis 7+.

## Installation

```bash
cp .env.example .env
pnpm install --frozen-lockfile
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "apps/api[dev]"
```

On Windows PowerShell, activate Python with `.venv/Scripts/Activate.ps1`. The example
environment uses Docker hostnames `postgres` and `redis`; native development must use
equivalent `localhost` URLs. Replace the example authentication secret outside local
development.

## Run with Docker

```bash
make up
```

The API entrypoint applies migrations, runs the idempotent agent seed, then starts
Uvicorn. Compose waits for healthy PostgreSQL and Redis first.

- Dashboard: <http://localhost:3000>
- API and OpenAPI: <http://localhost:8000>, <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Use `make down` and `make logs` to stop or inspect the stack.

## Run without Docker

Start PostgreSQL and Redis, configure `.env`, then:

```bash
make migrate
make seed
cd apps/api && uvicorn app.main:app --reload
```

In another terminal run `pnpm dev`. The login and registration pages still render if
the API is offline and present accessible request errors.

## Authentication endpoints

| Endpoint                     | Purpose                                     |
| ---------------------------- | ------------------------------------------- |
| `POST /api/v1/auth/register` | Create a user and authenticated session     |
| `POST /api/v1/auth/login`    | Verify credentials and create a session     |
| `POST /api/v1/auth/refresh`  | Rotate the refresh token and issue access   |
| `POST /api/v1/auth/logout`   | Revoke the current refresh token and cookie |
| `GET /api/v1/auth/me`        | Return the Bearer-authenticated active user |

The dashboard stores the access token in module memory only. The opaque refresh token
is stored only as a SHA-256 hash in PostgreSQL and sent as an HttpOnly cookie scoped to
`/api/v1/auth`. See the authentication document for rotation and reuse handling.

## Command workflow

All workflow endpoints require a valid Bearer access token. The backend resolves
ownership at every level; a foreign command, plan, or task is returned as not found.

| Endpoint                                 | Purpose                             |
| ---------------------------------------- | ----------------------------------- |
| `POST /api/v1/commands`                  | Create an owned pending command     |
| `GET /api/v1/commands`                   | List commands with safe pagination  |
| `GET /api/v1/commands/{id}`              | Read an owned command               |
| `POST /api/v1/commands/{id}/cancel`      | Cancel a non-terminal command       |
| `POST`, `GET /api/v1/commands/{id}/plan` | Create or read the command plan     |
| `POST`, `GET /api/v1/plans/{id}/tasks`   | Add or list ordered tasks           |
| `GET`, `PATCH /api/v1/tasks/{id}`        | Read or edit non-status task fields |
| `POST /api/v1/tasks/{id}/transition`     | Apply a validated transition        |

The authenticated UI is available at `/dashboard/commands`, with creation at
`/dashboard/commands/new` and detail at `/dashboard/commands/{id}`. Command detail can
generate a Supervisor proposal, show tasks and usage metadata, approve the plan, request
changes, and inspect prior versions. No task is executed.

## Supervisor planning

`POST /api/v1/commands/{id}/generate-plan` creates a draft plan through the configured
provider. `POST /api/v1/commands/{id}/regenerate-plan` supersedes a current draft using
bounded feedback. Approval moves the plan and tasks to `ready`; rejection keeps the
historical version and returns the command to `pending`. Runs and plan versions are
available through `GET /commands/{id}/supervisor-runs`, `GET /commands/{id}/plans`, and
`GET /plans/{id}`.

Set `AI_PROVIDER=openai`, `OPENAI_MODEL`, and `OPENAI_API_KEY` to use the provider.
FastAPI still starts and `/health` remains healthy without a key; an AI request then
fails safely with HTTP 503. CI uses an injected fake and makes no external AI call. The
command text is sent to the configured provider, so do not submit passwords, API keys,
or other secrets.

## Migrations and maintenance

Alembic reads `DATABASE_URL` from application settings.

```bash
cd apps/api
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"
python -m app.scripts.seed_agents
python -m app.scripts.cleanup_refresh_tokens
python -m app.scripts.test_supervisor_provider  # optional, requires OPENAI_API_KEY
```

The cleanup command deletes expired tokens and tokens revoked longer than
`AUTH_CLEANUP_RETENTION_DAYS`; it is explicit and has no scheduler.

## Health endpoints

- `GET /health` is process liveness and does not contact dependencies.
- `GET /ready` checks PostgreSQL and Redis, returning HTTP 503 with per-service status
  if either is unavailable.

Neither response exposes connection strings, credentials, or stack traces.

## Main commands

| Command                     | Purpose                                      |
| --------------------------- | -------------------------------------------- |
| `make up`, `down`, `logs`   | Operate the Docker Compose stack             |
| `make migrate`              | Apply pending Alembic migrations             |
| `make migration name="..."` | Generate an Alembic migration                |
| `make seed`                 | Seed the five initial agents idempotently    |
| `make cleanup-auth`         | Remove expired and old revoked refresh data  |
| `make test-ai`              | Run the optional real provider smoke test    |
| `make test`                 | Run frontend and backend tests               |
| `make lint`, `format`       | Lint or format all project code              |
| `make typecheck`            | Run TypeScript checks                        |
| `make ci`                   | Run the principal local CI-equivalent checks |

## Continuous integration

GitHub Actions runs on pushes and pull requests to `main`. Backend CI installs Python
3.12, runs Ruff, validates Alembic upgrade and the newest downgrade offline, and runs
Pytest with an explicitly fake AI provider.
Frontend CI installs Node.js 22 and pnpm, then runs ESLint, TypeScript, Vitest, and the
Next.js production build. No job requires repository secrets, PostgreSQL, or Redis.

## Repository structure

```text
.
|-- .github/workflows/ci.yml
|-- apps
|   |-- api
|   |   |-- alembic
|   |   |-- app
|   |   |   |-- ai
|   |   |   |-- api
|   |   |   |-- core
|   |   |   |-- db
|   |   |   |-- models
|   |   |   |-- repositories
|   |   |   |-- schemas
|   |   |   |-- scripts
|   |   |   |-- security
|   |   |   `-- services
|   |   `-- tests
|   `-- web
|       |-- app
|       |-- lib
|       `-- tests
|-- packages/shared
|-- docs
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Current limitations

- No social login, password recovery, organizations, or advanced permissions.
- No automatic refresh-token cleanup scheduler.
- Fixed-window rate limiting is intentionally simple.
- The OpenAI provider requires a separately supplied key and enabled compatible model;
  normal tests never call it.
- Prompt injection has defense in depth, not a claim of complete prevention.
- No background work or real multi-agent task execution.
- A real PostgreSQL/Redis container flow requires Docker and cannot be proven by static

## Execution Engine

Phase 3C adds registered, schema-bound internal tools, effective-risk enforcement,
fingerprinted approvals, immutable execution attempts, controlled retries, task
dependencies, audit events, automatic workflow progression, and best-effort cancellation.
PostgreSQL remains authoritative; a transactional outbox bridges commits to Celery over
Redis. The worker and outbox dispatcher run as separate Docker Compose services.

Authenticated execution endpoints cover Task Actions, dispatch/cancel, attempts,
approvals, dependencies, progress, and Command activity. The dashboard exposes
`/dashboard/executions` and `/dashboard/approvals`. See
[execution engine](docs/execution-engine.md), [tools](docs/tools.md), and
[approvals](docs/approvals.md).

Only safe internal and simulated tools exist. No real external integration or automatic
agent tool selection is included.
validation alone when Docker is unavailable.
