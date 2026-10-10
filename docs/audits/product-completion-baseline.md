# Kiko product-completion baseline

**Audit date:** 2026-10-10  
**Audited revision:** `80f1226` (`main`)  
**Production target inspected:** `https://kiko.pixart.pt`  
**Safety boundary:** repository and public/read-only HTTP inspection only; no production data or configuration was changed.

## Executive assessment

Kiko is a substantial governed-automation foundation, but it is not yet a commercially complete multi-tenant product. The current release contains authenticated commands, Supervisor planning, task execution, approvals, four specialist agents, CRM foundations, Gmail and Google Calendar adapters, Marketing, Automations, Knowledge, GitHub/Codex controls, observability, backup helpers, and production-oriented container definitions.

The release is nevertheless **NOT READY — BLOCKERS REMAIN**. The most important blockers are:

1. the deployed registration bundle calls a non-resolving API hostname;
2. tenant isolation exists only for Knowledge, while most business records remain user-scoped;
3. authentication lacks email verification, recovery/reset, session management, account lifecycle, legal acceptance, and the required role model;
4. there is no first-run onboarding, invitation lifecycle, subscription/entitlement layer, notification center, public commercial site, or first-class conversational Kiko workspace;
5. the UI exposes only a subset of backend capabilities and has no browser E2E, responsive, or accessibility release gate.

Passing unit tests demonstrate useful internal correctness, not commercial readiness.

## Evidence collected

- Backend: Ruff passed; formatting passed; policy suite passed 6/6; Pytest passed 203 tests, skipped 5 integration tests.
- Frontend: ESLint and TypeScript passed; Vitest passed 39 tests across 16 files.
- Database: one Alembic head, `20260920_0015`; offline history is linear.
- Production public checks: `/health` and `/ready` returned HTTP 200; database and Redis reported healthy.
- Production CORS preflight for `POST /api/v1/auth/register` returned HTTP 200 and allowed `https://kiko.pixart.pt`.
- Production registration API route exists (`GET` returns the expected HTTP 405 with `Allow: POST`).
- No registration POST was sent because that would create production data.

## Root cause of the installed registration failure

The public JavaScript bundle served by `https://kiko.pixart.pt/register` contains:

```text
NEXT_PUBLIC_API_URL=https://kiko.nodera.pt
```

The hostname `kiko.nodera.pt` did not resolve during the audit. The healthy API and valid CORS configuration are available on `https://kiko.pixart.pt`. Consequently, the browser attempts registration against an unavailable host before the request can reach the working FastAPI route.

This is a build/deployment configuration defect, not evidence that PostgreSQL, Redis, the registration route, or CORS is unavailable. The release package must build the web image with the correct public API origin (preferably same-origin) and include a post-build assertion that rejects unexpected API hosts. Production remediation remains behind the explicit release gate.

## Functional inventory

| Capability                           | Current state                      |                  E2E | Production-ready | Severity / primary gap                                            |
| ------------------------------------ | ---------------------------------- | -------------------: | ---------------: | ----------------------------------------------------------------- |
| Public website                       | Missing                            |                   No |               No | HIGH — `/` redirects directly to dashboard                        |
| Registration                         | Implemented, deployed incorrectly  |                   No |               No | BLOCKER — bad compiled API host; no legal consent or verification |
| Login/logout/refresh                 | Implemented                        |              Partial |               No | HIGH — no real browser journey or session UI                      |
| Email verification                   | Missing                            |                   No |               No | BLOCKER                                                           |
| Password recovery/reset/change       | Missing                            |                   No |               No | BLOCKER                                                           |
| Session listing/revocation           | Missing                            |                   No |               No | HIGH                                                              |
| Profile/deactivation/deletion        | Missing                            |                   No |               No | HIGH                                                              |
| Platform/workspace roles             | Partial                            |                   No |               No | BLOCKER — only Knowledge membership roles exist                   |
| Workspaces                           | Partial                            |       Knowledge only |               No | BLOCKER — business resources are not workspace-scoped             |
| Invitations and ownership transfer   | Missing                            |                   No |               No | BLOCKER                                                           |
| Onboarding                           | Missing                            |                   No |               No | HIGH                                                              |
| Kiko conversational workspace        | Missing                            |                   No |               No | BLOCKER — command form is not persistent conversation             |
| Commands and plans                   | Partial                            |  API/component tests |               No | HIGH — incomplete lifecycle/search/archive/duplicate              |
| Tasks                                | Partial                            |  API/component tests |               No | HIGH — no full assignment/project/filtered product UX             |
| Projects                             | Partial CRM projects               |                   No |               No | HIGH — not a general project-management product                   |
| Specialized agents                   | Implemented foundation             |  Fake-provider tests |               No | HIGH — configuration/status/performance incomplete                |
| Approval Center                      | Implemented foundation             |  API/component tests |               No | HIGH — comments/history/separation-of-duty incomplete             |
| CRM                                  | Substantial backend, read-heavy UI |  API/component tests |               No | HIGH — incomplete UI CRUD/import/export/duplicate flows           |
| Gmail                                | Real adapter plus fake tests       | No real provider E2E |               No | HIGH — test credentials and release validation required           |
| Google Calendar                      | Real adapter plus fake tests       | No real provider E2E |               No | HIGH — write journey and recurrence incomplete                    |
| Marketing                            | Implemented foundation             |  API/component tests |               No | MEDIUM/HIGH — incomplete product workflow and provider publishing |
| Automations                          | Implemented foundation             |  API/component tests |               No | HIGH — builder/edit/webhook/event coverage incomplete             |
| Knowledge                            | Workspace-scoped CRUD/search       |            API tests |          Partial | HIGH — document ingestion/indexing/deletion missing               |
| GitHub                               | Governed tool adapter              |           Fake tests |               No | HIGH — connection UX and real test account validation missing     |
| Codex                                | Controlled runner foundation       |           Fake tests |               No | HIGH — dedicated hardened runtime evidence missing                |
| Integrations Center                  | Partial                            |      Component tests |               No | MEDIUM — incomplete provider/status/configuration model           |
| Analytics                            | Missing product analytics          |                   No |               No | HIGH                                                              |
| Notifications                        | Missing                            |                   No |               No | HIGH                                                              |
| Personal/workspace/platform settings | Missing                            |                   No |               No | HIGH                                                              |
| Plans/entitlements/subscriptions     | Missing                            |                   No |               No | BLOCKER for commercial launch                                     |
| Data import/export/retention         | Missing                            |                   No |               No | HIGH                                                              |
| Observability                        | Foundation implemented             |           Unit tests |          Partial | MEDIUM — alerting/queue/provider/cost dashboards absent           |
| Backup/restore                       | Helpers documented                 | No staging rehearsal |               No | HIGH                                                              |
| Responsive/accessibility QA          | Unproven                           |                   No |               No | HIGH                                                              |
| Production deployment package        | Partial compose/docs               |    No full rehearsal |               No | BLOCKER                                                           |

## Tenant-isolation audit

`workspaces`, `workspace_members`, `knowledge_items`, and `knowledge_revisions` are workspace-scoped. The remaining core records are not. Commands, plans, tasks, executions, approvals, agent runs, integrations, CRM, Marketing, Automations, Email/Calendar references, and Codex runs are directly or transitively user-scoped.

This creates two product defects:

- colleagues in the same company do not share the same operational data safely;
- workspace roles cannot govern most business operations.

Current user scoping prevents a simple anonymous cross-user read in many services, but it is not the required company tenant model and cannot satisfy the two-workspace isolation acceptance journey. All relevant root aggregates need a non-null `workspace_id`, indexed ownership queries, membership/role dependencies, migration/backfill rules, and PostgreSQL integration tests.

## Authentication and user-management audit

Implemented:

- normalized email registration;
- Argon2 password hashing;
- duplicate-email handling;
- access tokens;
- rotating hashed refresh tokens with replay-family revocation;
- logout;
- inactive-user denial;
- basic Redis-backed rate limiting;
- non-enumerating login failure messages.

Missing or incomplete:

- Terms and Privacy acceptance fields and immutable evidence;
- email verification tokens, expiry, one-shot use, resend throttling, and delivery;
- recovery/reset/change-password flows;
- current sessions and selective/global revocation;
- profile editing, deactivation, deletion, and retention policy;
- platform super-admin separation;
- Workspace Owner/Admin/Manager/Member/Viewer enforcement across modules;
- MFA for privileged accounts;
- explicit CSRF strategy for cookie-authenticated endpoints;
- production browser E2E evidence.

## UI and experience audit

- Navigation is a wide row of links and omits Kiko AI, Tasks, Projects, Activity, Analytics, Team, and Settings.
- There is no mobile navigation or demonstrated tablet/mobile layout.
- The dashboard declares every catalog agent `Ready` regardless of provider configuration or operational evidence.
- `/` redirects to `/dashboard`; there is no commercial landing experience.
- Unauthenticated users reach a dashboard loading shell before client-side redirection.
- Registration lacks Terms/Privacy acceptance, verification feedback, and recovery routes.
- The primary product interaction is command creation rather than a persistent conversation workspace.
- Several backend mutations have no complete UI workflow; CRM and Marketing pages are primarily lists/search.
- Empty/loading/error states exist inconsistently and no browser-level audit currently covers them.

## API and persistence audit

- Route/service/repository separation is generally consistent.
- Migrations form one linear head and include downgrade operations.
- CI includes a PostgreSQL/Redis job for execution locking/outbox behavior, but most tests use SQLite and five local integration tests were skipped without running the services.
- There are no PostgreSQL multi-tenant isolation tests because most tables are not tenant-scoped.
- API coverage is incomplete for required CRUD lifecycles: commands lack duplicate/archive/search; projects are not a standalone aggregate; user/team/settings/subscriptions/notifications are absent.
- Database migration policy needs a staged backfill before non-null tenant constraints can cover existing records.

## Integration and execution audit

- OpenAI, Gmail, Google Calendar, GitHub, and Codex have real adapter code and fail-closed configuration switches.
- CI uses fake providers and cannot prove real credentials, OAuth redirects, provider delivery, or reconciliation.
- Approval fingerprints, idempotency records, allowlists, protected branches, and delivery-unknown concepts are useful foundations.
- No external provider was enabled or invoked during this audit.
- The Codex runner has filesystem and command controls in application code, but a dedicated runtime identity, network policy, host credential separation, and resource enforcement are not proven by the current Compose package.

## Security and reliability findings

### BLOCKER

- Production web bundle targets a non-resolving API hostname.
- Core business data is not workspace-scoped.
- Required verified-identity and account-recovery lifecycle is absent.
- Commercial entitlement enforcement is absent.

### HIGH

- Workspace role model is isolated to Knowledge and lacks invitations/lifecycle.
- No E2E browser suite for critical journeys.
- No complete privileged platform-admin boundary or MFA.
- No document-upload security pipeline.
- No staging backup/restore rehearsal evidence.
- No dedicated infrastructure isolation evidence for Codex Runner.
- No first-run onboarding or persistent conversation model.
- No notification, settings, data-portability, or account-lifecycle product surfaces.

### MEDIUM

- Dashboard presents configured agents as `Ready` without checking provider availability.
- Production image configuration is build-time and lacks an origin assertion.
- Metrics exist but there is no authorized operational dashboard or alerting integration.
- Current public responses expose framework/server identifiers (`Next.js`, `uvicorn`); this is not a direct vulnerability but can be reduced at the reverse proxy.

### LOW

- Test run emits a Starlette/AnyIO deprecation warning.
- Naming still mixes `Agent` and `Kiko` in user-visible copy and package metadata.

## Commercial completion backlog

The backlog follows dependency order; BLOCKER/HIGH work must be completed before polish.

### R0 — Audit and root cause

- [x] Update and inspect latest `main`.
- [x] Inventory routes, models, migrations, tests, deployment artifacts, and UI routes.
- [x] Run current static/unit gates.
- [x] Diagnose registration without production mutation.
- [ ] Add a release-safe web API-origin contract and deployment assertion.
- [ ] Run clean PostgreSQL migration upgrade/downgrade and Redis integration tests locally or in CI evidence.

### R1 — Identity and onboarding

- [ ] Extend user/account schema for verified email, profile, status, legal acceptance, and platform role.
- [ ] Implement one-shot hashed verification and password-reset tokens with throttled resend.
- [ ] Implement session inventory/revocation and password change.
- [ ] Complete workspace profile/lifecycle, roles, invitations, switching, and ownership transfer.
- [ ] Tenant-scope all business roots with staged backfill and server-side membership enforcement.
- [ ] Add onboarding persistence and first-success journey.
- [ ] Add PostgreSQL cross-tenant adversarial tests and browser Journey A/B/H.

### R2 — Core Kiko experience

- [ ] Persist conversations/messages and route actions exclusively through Supervisor/Execution Engine.
- [ ] Complete command/task/project lifecycle and views.
- [ ] Complete Agent Center configuration and operational status.
- [ ] Complete approval comments/history/expiry and separation-of-duty policy.

### R3 — Business modules

- [ ] Complete CRM UI CRUD, pipeline, duplicate handling, import/export, and Client 360.
- [ ] Validate Gmail and Calendar with authorized test accounts and reconciliation states.
- [ ] Complete Marketing and Automation builders/lifecycles.
- [ ] Add safe document ingestion and grounded retrieval.

### R4 — Enterprise experience

- [ ] Add notifications, activity, analytics, settings, team administration, and platform administration.
- [ ] Add governed integration configuration and data portability/retention workflows.

### R5 — Commercial layer

- [ ] Add plan, entitlement, trial, subscription, and provider-abstracted billing records.
- [ ] Build the public product site without unverifiable claims.

### R6 — Product polish

- [ ] Establish the Kiko design system, responsive shell, accessible interactions, and complete states.
- [ ] Remove dead/misleading controls and false readiness labels.

### R7 — Security and reliability

- [ ] Complete ASVS/API threat review and adversarial regression suite.
- [ ] Validate migrations, rollback, concurrency, performance, observability, recovery, and runner isolation.
- [ ] Add comprehensive E2E, responsive, accessibility, console, and network gates.

### R8 — Demo and release candidate

- [ ] Provision isolated staging procedure and two test-account procedure.
- [ ] Implement and rehearse the clearly synthetic investor demo.
- [ ] Complete product/operator documentation and immutable deployment package.
- [ ] Generate `docs/releases/KIKO-COMMERCIAL-RELEASE-READINESS.md` and stop at the production release gate.

## Immediate implementation order

1. Fix and guard the public API-origin build contract.
2. Implement the complete identity lifecycle.
3. Expand Workspace into the canonical tenant boundary and migrate all business aggregates.
4. Implement invitations, roles, switching, onboarding, and isolation tests.
5. Only then advance to conversational Kiko and the remaining business/commercial phases.

## Baseline verdict

**NOT READY — BLOCKERS REMAIN**
