# Agent roadmap

## Fase 1 — Fundação

- Establish the Next.js and FastAPI monorepo.
- Provide local PostgreSQL and Redis services.
- Add baseline linting, formatting, tests, and documentation.
- Expose the initial agent catalog and system health.

## Fase 2 — Autenticação e utilizadores

- Introduce user accounts, sessions, and role-based permissions.
- Create the first PostgreSQL schema and migrations.
- Add secure audit trails for sensitive actions.

## Fase 3 — Supervisor e execução de tarefas

- Define the task and execution lifecycle.
- Implement Supervisor planning and delegation.
- Persist progress, artifacts, errors, and approvals.
- Add safe background execution and cancellation.

## Fase 4 — Agentes especializados

- Implement Marketing, Sales, Support, and Development capabilities.
- Define per-agent tools, boundaries, and evaluation criteria.
- Add reusable workflows and human approval checkpoints.

## Fase 5 — Integrações externas

- Connect selected communication, CRM, support, and development systems.
- Add credential management and granular integration permissions.
- Introduce event-driven triggers and scheduled work.

## Fase 6 — Observabilidade e produção

- Add structured logs, metrics, tracing, alerts, and cost monitoring.
- Harden security, backups, recovery, and deployment practices.
- Add load, reliability, and agent-quality evaluations.
- Define production service-level objectives and operating procedures.
