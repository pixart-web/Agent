# Agent roadmap

## Fase 1 — Fundação

- [x] Establish the Next.js and FastAPI monorepo.
- [x] Provide PostgreSQL, Redis, migrations, readiness, and CI.
- [x] Persist and seed the initial agent catalog.

## Fase 2 — Autenticação e utilizadores

- [x] Persist normalized users and hashed rotating refresh tokens.
- [x] Add register, login, refresh, logout, and authenticated-user endpoints.
- [x] Add Argon2id passwords, JWT access tokens, HttpOnly cookies, and reuse detection.
- [x] Add Redis rate limiting and explicit refresh-token cleanup.
- [x] Add login, registration, protected dashboard, tests, migration, CI, and docs.
- [ ] Add security audit trails when sensitive administrative actions are introduced.

## Fase 3 — Supervisor e execução de tarefas

- [x] **3A:** Persist owned commands, plans, tasks, explicit transitions,
      status history, authenticated UI, migration, and tests.
- [x] **3B:** Add provider-neutral Supervisor planning, structured OpenAI output,
      versioned plans, human approval/replanning, risk guardrails, UI, and audited runs.
- [x] **3C:** Add registered internal tools, Celery workers, transactional outbox,
      fingerprinted approvals, retries, dependencies, cancellation, audit logs,
      execution dashboards, PostgreSQL/Redis integration tests, and state propagation.

## Fase 4 — Agentes especializados

- [x] Implement Marketing, Sales, Support, and Development capabilities.
- [x] Define per-agent tools, boundaries, and evaluation criteria.
- [x] Add reusable workflows and human approval checkpoints.

## Fase 5 — Integrações externas

- [ ] Connect selected communication, CRM, support, and development systems.
- [ ] Add credential management and granular integration permissions.
- [ ] Introduce event-driven triggers and scheduled work.

## Fase 6 — Observabilidade e produção

- [ ] Add structured logs, metrics, tracing, alerts, and cost monitoring.
- [ ] Harden security, backups, recovery, and deployment practices.
- [ ] Add load, reliability, and agent-quality evaluations.
- [ ] Define production service-level objectives and operating procedures.
