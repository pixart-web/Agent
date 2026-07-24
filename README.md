# Agent

Agent is Pixart's multi-agent operations platform. This monorepo provides a Next.js
dashboard, a FastAPI API, PostgreSQL persistence, Redis infrastructure, secure user
authentication, migrations, and continuous integration. OpenAI integration and real
agent execution remain deliberately out of scope.

## Architecture

- **Web:** Next.js 15 App Router, React, and TypeScript.
- **API:** FastAPI on Python 3.12.
- **Persistence:** SQLAlchemy 2 with explicit sessions and PostgreSQL.
- **Authentication:** Argon2id passwords, short JWT access tokens, and rotating opaque
  refresh tokens in HttpOnly cookies.
- **Infrastructure:** Redis for readiness and authentication rate limiting.
- **Migrations:** Alembic configured from application settings.
- **Local environment:** Docker Compose for web, API, PostgreSQL, and Redis.
- **CI:** independent backend and frontend jobs in GitHub Actions.

Domain requests follow:

```text
HTTP route -> service -> repository -> SQLAlchemy session -> PostgreSQL
```

Authentication details are in [docs/authentication.md](docs/authentication.md);
system boundaries are in [docs/architecture.md](docs/architecture.md).

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

## Migrations and maintenance

Alembic reads `DATABASE_URL` from application settings.

```bash
cd apps/api
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"
python -m app.scripts.seed_agents
python -m app.scripts.cleanup_refresh_tokens
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
| `make test`                 | Run frontend and backend tests               |
| `make lint`, `format`       | Lint or format all project code              |
| `make typecheck`            | Run TypeScript checks                        |
| `make ci`                   | Run the principal local CI-equivalent checks |

## Continuous integration

GitHub Actions runs on pushes and pull requests to `main`. Backend CI installs Python
3.12, runs Ruff, validates Alembic offline, and runs Pytest with explicit test settings.
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
- No OpenAI integration or real multi-agent execution.
- A real PostgreSQL/Redis container flow requires Docker and cannot be proven by static
  validation alone when Docker is unavailable.
