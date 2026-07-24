# Agent

Agent is the foundation for Pixart's multi-agent operations system. It provides a
single place to coordinate automation across marketing, sales, support, development,
and company-wide supervision.

This initial version intentionally contains no authentication, OpenAI integration, or
agent execution logic. It establishes a small, testable platform that can evolve safely.

## Architecture

- **Web:** Next.js 15, App Router, React, and TypeScript.
- **API:** FastAPI on Python 3.12, organized by routes, configuration, schemas, models,
  and services.
- **Database:** PostgreSQL, provisioned locally and ready for future persistence.
- **Cache and queues:** Redis, provisioned for future caching and background work.
- **Shared package:** TypeScript contracts and catalog data used by the web application.
- **Local environment:** Docker Compose coordinates all four services.

See [docs/architecture.md](docs/architecture.md) for the system boundaries and
[docs/roadmap.md](docs/roadmap.md) for the planned phases.

## Requirements

### Docker workflow

- Docker Engine or Docker Desktop
- Docker Compose v2
- Make (optional, but recommended)

### Native workflow

- Node.js 22+
- pnpm 11+
- Python 3.12+
- PostgreSQL 16+ and Redis 7+ when testing future persistence features

## Installation

Copy the example environment file and keep local secrets out of version control:

```bash
cp .env.example .env
```

For a native installation:

```bash
pnpm install
python -m venv apps/api/.venv
source apps/api/.venv/bin/activate
python -m pip install -e "apps/api[dev]"
```

On Windows PowerShell, activate the environment with
`apps/api/.venv/Scripts/Activate.ps1`.

## Run with Docker

```bash
make up
```

The dashboard is available at <http://localhost:3000>, the API at
<http://localhost:8000>, and interactive API documentation at
<http://localhost:8000/docs>.

Stop the stack with:

```bash
make down
```

## Run without Docker

Start the API:

```bash
cd apps/api
uvicorn app.main:app --reload
```

In another terminal, start the web application:

```bash
pnpm dev
```

The current API endpoints do not depend on PostgreSQL or Redis, so both applications
can run without those services during this foundation phase.

## Main commands

| Command       | Purpose                                       |
| ------------- | --------------------------------------------- |
| `make up`     | Build and start the local stack               |
| `make down`   | Stop the local stack                          |
| `make logs`   | Follow Docker Compose logs                    |
| `make test`   | Run the FastAPI Pytest suite                  |
| `make lint`   | Run ESLint and Ruff                           |
| `make format` | Format TypeScript, Markdown, JSON, and Python |
| `pnpm build`  | Create a production frontend build            |

## Repository structure

```text
.
├── apps
│   ├── api              # FastAPI service and tests
│   └── web              # Next.js dashboard
├── packages
│   └── shared           # Shared TypeScript contracts
├── docs
│   ├── architecture.md
│   └── roadmap.md
├── .env.example
├── docker-compose.yml
├── Makefile
└── README.md
```
