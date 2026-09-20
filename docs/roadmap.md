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

- [x] **5A:** Add the allowlisted GitHub client, scoped Development tools,
      runtime credentials, policy enforcement, approvals, audit events, status UI,
      fake integration tests, and operator documentation.
- [x] **5A.2:** Add governed Codex CLI execution, isolated workspaces, persistent runs,
      fixed repository validation profiles, approvals, security policies, dashboards,
      fake-runner tests, smoke test, and operator documentation.
- [x] **5B:** Add provider-neutral email, Gmail OAuth, encrypted refresh tokens,
      governed Support/Sales tools, idempotent writes, safe dashboards, tests, and docs.
- [x] **5C:** Add governed Google Calendar integration with approval-gated writes.
- [x] **5D:** Add user-scoped Contacts / CRM foundation with governed identity links.

## Fase 6 — Complete CRM / client management

- [x] Add governed client profiles, projects, pipelines, opportunities, ownership and history.
- [x] Add a user-scoped Client 360 view with contacts, references, tasks, notes and activity.
- [x] Distinguish database facts from model-generated summaries in contracts and UI.

## Fase 7 — Marketing & content operations

- [x] Add governed campaigns, content, approvals and publication lifecycle.

## Fase 8 — Automations

- [ ] Add governed triggers, schedules, runs, pause/resume and failure recovery.

## Fase 9 — Memory, business knowledge & workspaces

- [ ] Add workspace-scoped memory, knowledge provenance, retrieval and permissions.

## Fase 10 — Production readiness

- [ ] Add observability, security hardening, backups, recovery and deployment practices.
- [ ] Add load, reliability, cost and agent-quality evaluations.
- [ ] Define production service-level objectives and operating procedures.
