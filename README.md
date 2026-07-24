# Agent

Agent is Pixart's multi-agent operations platform. The project currently provides a
production-oriented foundation for a web dashboard, a versioned API, persistent agent
records, dependency readiness checks, migrations, and continuous integration.

Authentication, OpenAI integration, and real agent execution are intentionally outside
this phase.

## Architecture

- **Web:** Next.js 15, App Router, React, and TypeScript.
- **API:** FastAPI on Python 3.12.
- **Persistence:** SQLAlchemy 2 with explicit synchronous sessions and PostgreSQL.
- **Migrations:** Alembic, configured from the same application settings as the API.
- **Readiness:** direct PostgreSQL and Redis availability checks.
- **Local environment:** Docker Compose coordinates web, API, PostgreSQL, and Redis.
- **CI:** independent backend and frontend jobs in GitHub Actions.

Agent reads follow this path:

```text
HTTP route -> service -> repository -> SQLAlchemy session -> PostgreSQL
```

See [docs/architecture.md](docs/architecture.md) for system boundaries and
[docs/roadmap.md](docs/roadmap.md) for planned phases.

## Requirements

### Docker workflow

- Docker Engine or Docker Desktop
- Docker Compose v2
- Make (optional, but recommended)

### Native workflow

- Node.js 22+
- pnpm 11+
- Python 3.12+
- PostgreSQL 16+
- Redis 7+

## Installation

Copy the example environment file:

```bash
cp .env.example .env
```

The example uses the Docker hostnames `postgres` and `redis`. For a fully native
environment, set `DATABASE_URL` and `REDIS_URL` to equivalent `localhost` URLs.

Install dependencies:

```bash
pnpm install
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "apps/api[dev]"
```

On Windows PowerShell, activate the environment with
`.venv/Scripts/Activate.ps1`.

## Run with Docker

```bash
make up
```

The API entrypoint waits for the Compose health dependencies, applies all migrations,
runs the idempotent agent seed, and then starts Uvicorn.

Services:

- Dashboard: <http://localhost:3000>
- API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Stop or inspect the stack with:

```bash
make down
make logs
```

## Run without Docker

Start PostgreSQL and Redis, then point the environment variables to those services.
Apply migrations and seed the initial records:

```bash
make migrate
make seed
```

Start the API:

```bash
cd apps/api
uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
pnpm dev
```

The frontend remains usable when the API is offline and reports that state in the
dashboard.

## Migrations

Alembic reads `DATABASE_URL` through the application settings.

```bash
cd apps/api
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"
```

Equivalent Make commands:

```bash
make migrate
make migration name="add task table"
```

## Initial seed

The explicit seed inserts the five initial agents and safely updates their managed
fields when definitions change. Repeated executions do not create duplicates.

```bash
cd apps/api
python -m app.scripts.seed_agents
```

Or:

```bash
make seed
```

## Health endpoints

- `GET /health` confirms only that the API process is running. It does not access
  external services.
- `GET /ready` checks PostgreSQL and Redis. It returns HTTP 200 when both are healthy
  and HTTP 503 with per-service availability when either dependency is unavailable.

Neither endpoint exposes credentials, connection URLs, or stack traces.
Dependency connection attempts use the configurable
`SERVICE_CONNECT_TIMEOUT_SECONDS` value.

## API endpoints

- `GET /`
- `GET /health`
- `GET /ready`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`

## Main commands

| Command                   | Purpose                                          |
| ------------------------- | ------------------------------------------------ |
| `make up`                 | Build and start the local Docker stack           |
| `make down`               | Stop the local Docker stack                      |
| `make logs`               | Follow Docker Compose logs                       |
| `make migrate`            | Apply pending Alembic migrations                 |
| `make migration name="…"` | Generate an Alembic migration                    |
| `make seed`               | Run the idempotent initial agent seed            |
| `make test`               | Run the backend Pytest suite                     |
| `make lint`               | Run ESLint and Ruff                              |
| `make format`             | Format frontend, documentation, and Python files |
| `make typecheck`          | Run TypeScript without emitting files            |
| `make ci`                 | Run the main local CI-equivalent checks          |

## Continuous integration

GitHub Actions runs on pushes and pull requests targeting `main`.

- The backend job installs Python 3.12 dependencies, runs Ruff, validates Alembic in
  offline mode, and runs Pytest.
- The frontend job installs Node.js 22 and pnpm through Corepack, restores the pnpm
  cache, runs ESLint and TypeScript checks, and builds Next.js.

The workflow needs no repository secrets and the backend tests use an isolated SQLite
database rather than external services.

## Repository structure

```text
.
|-- .github/workflows/ci.yml
|-- apps
|   |-- api
|   |   |-- alembic
|   |   |-- app
|   |   |   |-- api
|   |   |   |-- db
|   |   |   |-- models
|   |   |   |-- repositories
|   |   |   |-- schemas
|   |   |   |-- scripts
|   |   |   `-- services
|   |   `-- tests
|   `-- web
|-- packages/shared
|-- docs
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Current limitations

- No authentication or authorization.
- No OpenAI or other model provider integration.
- No real multi-agent orchestration or background queue.
- Docker execution requires Docker Engine; static validation alone cannot prove local
  container startup when Docker is unavailable.
