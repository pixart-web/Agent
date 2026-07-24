# Agent architecture

## System overview

Agent starts as a modular monorepo with a browser-based operations dashboard and a
versioned HTTP API. PostgreSQL and Redis are part of the local topology from day one,
while business data persistence and asynchronous processing remain intentionally
deferred.

```text
Browser -> Next.js web -> FastAPI
                           |  |
                           |  +-> Redis (future cache and queues)
                           +----> PostgreSQL (future system of record)
```

## Frontend

`apps/web` contains a Next.js App Router application written in TypeScript. The first
dashboard displays API availability and the five initial agents. It uses browser-native
features and custom CSS rather than a UI framework. `NEXT_PUBLIC_API_URL` defines the
API base URL.

## Backend

`apps/api` contains the FastAPI service. Its packages separate HTTP routes (`api`),
settings and infrastructure (`core`), future persistence entities (`models`), validated
contracts (`schemas`), and application behavior (`services`). All configuration is read
from environment variables, and CORS initially allows the local frontend origin.

The initial public endpoints are:

- `GET /`
- `GET /health`
- `GET /api/v1/agents`

## PostgreSQL

PostgreSQL will become the durable system of record for users, tasks, agent runs,
artifacts, permissions, and audit data. The foundation only provisions the service; no
schema or ORM is introduced until the required domain model is clear.

## Redis

Redis is reserved for short-lived caching, distributed coordination, rate limiting, and
future task queues. No queue framework is selected during the foundation phase.

## Future multi-agent orchestration

A later orchestration layer will receive tasks, ask the Supervisor to plan and delegate
work, execute specialized capabilities, persist state, and expose progress to the
dashboard. It should keep agent definitions separate from providers and tools so that
models, integrations, and execution policies can evolve independently.

## Initial agent responsibilities

| Agent           | Initial responsibility                                             |
| --------------- | ------------------------------------------------------------------ |
| **Supervisor**  | Prioritize work, delegate tasks, coordinate agents, track outcomes |
| **Marketing**   | Support campaigns, content, brand, and marketing operations        |
| **Sales**       | Support pipeline, proposals, outreach, and commercial follow-up    |
| **Support**     | Triage requests, organize knowledge, and assist customer service   |
| **Development** | Support delivery, technical planning, quality, and maintenance     |
