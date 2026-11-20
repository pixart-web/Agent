# Kiko — Full QA report (macOS release candidate 0.2.0)

**Date:** 2026-11-15 · **Branch:** `qa/kiko-full-system-hardening` · **Baseline:** `main` @
`f9e1945` (PR #33) · **Release candidate built from:** `cf645d0` (clean tree) · **Machine:**
Mac mini M4, 32 GB, macOS 27.2.

## 1. Executive summary

The program combined the full QA/hardening plan with the mandatory **local-AI-only** directive
(which takes precedence). Outcome:

- **AI is now 100 % local.** OpenAI was removed; every AI flow (Supervisor, Kiko AI, specialist
  agents, summarisation, automation planning) runs on `gemma4:12b-it-qat` through Ollama on the
  Mac. A real-model evaluation passes **25/25 checks** and every network connection of the API,
  worker and runtime was loopback. Codex (external inference) is excluded.
- **15 defects recorded**; all CRITICAL/HIGH ones are fixed with regression tests. Notable:
  a critical Next.js RCE advisory, the desktop app cutting AI generation off at 30 s, specialist
  agents failing with real models, dispatchers dying on a database restart, tests that only
  passed on SQLite, accessibility violations.
- **Test evidence:** backend 293 tests on PostgreSQL 16 + Redis (0 skipped) and 287 passed / 6
  skipped on SQLite · web 64 · Rust 21 · real macOS app journey with real local AI (29 UI steps) · AI eval
  25/25 · IDOR sweep over 93 operations (0 leaks) · Playwright quality sweep of 21 screens
  (desktop + mobile, 0 findings) · dependency audits clean (npm, PyPI) · CI green.
- **Decision: READY FOR OWNER ACCEPTANCE TESTING.** Not ready for deployment preparation: the
  production inference host, HTTPS staging backend, Apple signing/notarisation and a real SMTP
  provider are owner decisions that remain open (section 24).

## 2. Git revision audited

| Item              | Value                                                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Starting point    | `main` @ `f9e1945d4529a4111bcb46497a69b0842849f4d2`, clean, CI green                                                                                                                       |
| Open PRs at start | Dependabot only (#20–#30); not merged (out of scope; the Next.js advisory was fixed here)                                                                                                  |
| QA branch commits | `9e73c23` local AI + QA hardening · `e9e47d2` agents/a11y/sweeps · `bbee00f` format · `950b015` resilient dispatchers · `a611b70` 0.2.0 + AI docs · `cf645d0` format · plus report commits |
| Alembic head      | `20261014_0035` (unchanged; no schema change was needed)                                                                                                                                   |

## 3. Architecture overview

FastAPI (192 operations, 27 routers) + PostgreSQL 16 + Redis + Celery worker + outbox and
transactional-email dispatchers; Next.js web client (static export inside the Tauri 2 macOS app,
which proxies all API calls through Rust and keeps the refresh token in the Keychain). AI:
`LLMProvider` → `OllamaProvider` → Ollama on loopback/private network → local model. Details:
`docs/desktop/KIKO-MACOS-ARCHITECTURE.md`, `docs/ai/KIKO-LOCAL-AI-ARCHITECTURE.md`.

## 4–5. Functional inventory and coverage matrix

See [KIKO-FUNCTIONAL-COVERAGE-MATRIX.md](KIKO-FUNCTIONAL-COVERAGE-MATRIX.md). Summary: identity,
AI, operations, approvals, execution, CRM contacts, knowledge, notifications, recovery and
multi-tenancy are **verified end to end**; organisations/opportunities, marketing, automations,
entitlements and project↔task association are **partially** verified (live creation + unit
tests); Gmail/Calendar/GitHub are **external** (disabled); Codex and external AI are **excluded**.

## 6. Test environment

`scripts/local/kiko-local.sh` (`docs/desktop/KIKO-LOCAL-TEST-ENVIRONMENT.md`): dedicated
PostgreSQL 16 (`:55432`), Redis (`:56379`), Mailpit, API `http://localhost:8000`, Celery
(`--pool=solo`), dispatchers, web dev server, the Mac's Ollama service (`:11434`, not modified).
Disposable databases `kiko_pytest_test`, `kiko_integration_test`, `kiko_migration_test` were
created for destructive tests; the owner's `kiko_local` data was preserved.

## 7–10. Tests executed / passed / failed / blocked

| Suite                           | Command                                                                                  | Result                                                                                                                                             |
| ------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend (SQLite, FK enforced)   | `pytest apps/api`                                                                        | **287 passed, 6 skipped** (integration tests need PostgreSQL/Redis)                                                                                |
| Backend (PostgreSQL 16 + Redis) | `TEST_DATABASE_URL=… INTEGRATION_DATABASE_URL=… INTEGRATION_REDIS_URL=… pytest apps/api` | **293 passed, 0 skipped** (CI also runs the full suite on PostgreSQL)                                                                              |
| Web unit/component              | `vitest run`                                                                             | **64 passed**                                                                                                                                      |
| Rust (desktop)                  | `cargo test`                                                                             | **21 passed**                                                                                                                                      |
| Backend smoke                   | `kiko-local.sh test`                                                                     | **20/20** (repeated ≥ 6×)                                                                                                                          |
| Restart recovery                | `restart` + `test-persisted`; each service individually                                  | **5/5** per service (one early 3/5 was the auth rate limit, not recovery)                                                                          |
| Real local-AI evaluation        | `kiko-local.sh ai-eval`                                                                  | **25/25** (final run; earlier 22–23/25 exposed KQA-005/008)                                                                                        |
| Real macOS app journey          | `kiko-local.sh desktop-e2e` (debug build, real WebView, Keychain, local AI)              | **all phases passed** in both runs after the final fixes                                                                                           |
| IDOR / cross-tenant             | `kiko-local.sh idor-sweep`                                                               | **93 operations, 0 leaks** (13 not covered: global agent catalog, disabled integrations, run ids)                                                  |
| UI quality / accessibility      | Playwright `dashboard-quality-sweep.spec.ts`                                             | **21 screens × 2 viewports, 0 findings** (after fixing KQA-015)                                                                                    |
| Live business workflows B/H/L/F | invitation, roles, knowledge FTS, entitlements, CRM export                               | **11/11**                                                                                                                                          |
| Performance                     | `kiko-local.sh perf`                                                                     | **12/12** (section 12)                                                                                                                             |
| Migrations                      | fresh upgrade, full downgrade to base, re-upgrade (disposable DB)                        | **pass**; `alembic check` reports model drift (KQA-010)                                                                                            |
| Dependency audits               | `pnpm audit`, `pip-audit`, `cargo audit`                                                 | **0 vulnerabilities** (cargo: 5 warnings, Linux-only crates)                                                                                       |
| CI (GitHub Actions)             | run 43712936480                                                                          | Backend, Frontend, PostgreSQL+Redis integration (incl. full suite on PostgreSQL), production container build: **success**; Desktop (macOS): see PR |

**Blocked / not executed:** real Gmail/Calendar/GitHub accounts (credentials), real SMTP,
Apple notarisation (no Developer ID), installation into `/Applications` (needs owner approval to
replace the installed 0.1.0), native menu/palette/save-panel clicks (no Accessibility-permitted
UI automation), physical network cut (egress sampling used instead).

## 11. Security findings

| Area                           | Result                                                                                                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dependencies                   | Next.js critical RCE + high DoS **fixed** (15.5.29); 22 dev-tool advisories **fixed**; PyPI clean; Rust 0 vulnerabilities                                                                                       |
| Cross-tenant / IDOR            | 93 operations probed with another company's ids: no 2xx                                                                                                                                                         |
| Authentication                 | refresh rotation; replaying an old refresh token → 401 and the newest token is revoked too (family revocation); foreign `Origin` → 403; forged, unsigned and `alg=none` JWTs → 401; Argon2id (64 MiB, t=3, p=4) |
| Authorisation                  | plain member cannot invite admins (403); plan approval required before task execution; external-effect tools wait for approval                                                                                  |
| Prompt / tool-output injection | real-model injection case: no exfiltration task, plan stayed `draft`; agent tool calls limited by schema to the allowlist; placeholder ids rejected                                                             |
| External AI egress             | configuration rejects public AI endpoints; runtime egress sampled: loopback only                                                                                                                                |
| File uploads                   | 5 MB limit, extension allowlist, strict PDF parsing, DOCX zip-bomb/encryption checks (code review)                                                                                                              |
| XSS / SQL injection            | no `dangerouslySetInnerHTML`/`innerHTML`/`eval`; no interpolated SQL (static review)                                                                                                                            |
| Redirects / SSRF               | OAuth callbacks redirect only to the configured web origin; outbound HTTP only to fixed provider hosts and the private AI endpoint                                                                              |
| Desktop IPC / deep links       | reviewed in PR #32/#33; deep links only navigate in-app, traversal rejected; AI timeouts scoped to 4 POST routes                                                                                                |
| Logging                        | no tokens/passwords/keys logged (static review)                                                                                                                                                                 |

No open BLOCKER/CRITICAL/HIGH security finding.

## 12. Performance results

Local AI (M4): plan generation p50 **43.5 s**, max 75.7 s; agent runs 21–22 s; summarisation
≈ 4.5 s; model RSS 7.96 GB. API: list endpoints p50 1.2–8.7 ms, p95 ≤ 10.8 ms; 200 requests at
concurrency 10 → 831 req/s, p95 15.5 ms, 0 errors. Release app idle: 96 MB RSS, 0 % CPU (earlier
measurement: 0.3–0.6 s from launch to first API call). Full tables:
`docs/ai/KIKO-LOCAL-AI-BENCHMARKS.md`.

## 13–15. Bugs discovered, fixed, unresolved

[KIKO-FULL-DEFECT-REGISTER.md](KIKO-FULL-DEFECT-REGISTER.md): 15 entries. Fixed: KQA-001
(BLOCKER), 003 (CRITICAL), 002/004/005/014 (HIGH), 006/007/008/009/015 (MEDIUM), plus 012/013 from
PR #33. Open: KQA-010 (LOW, model/migration drift, documented). Accepted: KQA-011 (LOW).

## 16. Improvements implemented

Local AI provider and policy enforcement; constrained agent schemas; desktop AI timeouts;
resilient dispatchers; PostgreSQL test mode + CI full-suite run; SQLite FK enforcement; dependency
upgrades; accessibility fixes; new tooling (`ai-eval`, `idor-sweep`, `perf`, dashboard sweep,
desktop `local-ai` phase); atomic env file and worker readiness check in `kiko-local.sh`.

## 17. Improvements recommended

[KIKO-PRODUCT-IMPROVEMENTS.md](KIKO-PRODUCT-IMPROVEMENTS.md) — top items: background AI jobs with
progress (E1/C1), align models with migrations (B1), production inference host (A1).

## 18. AI provider validation

Local only: `gemma4:12b-it-qat` via Ollama 0.40.16. Validated: Supervisor (28/28 generations
across 4 runs), conversation, agents (2/2 valid in the final run), summarisation, approvals,
injection resistance, tenant isolation, runtime outage and recovery, network independence.
`qwen3.5:9b`/`4b` failed the schema test and are not used. No external AI provider was used at
any point. Reports: `~/.kiko-local/ai-eval/`. Docs: `docs/ai/`.

## 19. External integration status

Gmail, Google Calendar, GitHub: implemented, disabled, not tested with real accounts. SMTP:
verified with Mailpit only. Codex and external AI: excluded by policy. Pixart ecosystem
integration points: unchanged (`docs/desktop/KIKO-PIXART-ECOSYSTEM.md`).

## 20. macOS application validation

Debug build journey (real WKWebView + Keychain + local AI): registration, verification,
onboarding, Keychain session restore, real AI plan generated and approved in the app, manual
plan, governed action approved and executed by the worker, task/project/CRM persistence across
relaunch, logout removes the Keychain item. Release 0.2.0 build: launches against the local API,
cold-start `kiko://verify-email` deep link verified an account, idle 96 MB/0 % CPU. Not
automated: native menus, palette, file dialogs, notification banners.

## 21. Database migration status

Head `20261014_0035`. On a disposable PostgreSQL 16 database: fresh upgrade OK, downgrade to
base OK, re-upgrade OK; CI also validates offline SQL and a real partial downgrade. Data
integrity under the application is covered by the full suite on PostgreSQL (foreign keys,
unique constraints, enums, full-text search). Open: model/migration drift (KQA-010). Backup and
restore: `app/scripts/backup_database.py` / `restore_database.py`, procedure in
`docs/production-readiness.md` and `docs/administrator-manual.md`.

## 22. Release artifact details

| Item         | Value                                                                                                                                                                 |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version      | 0.2.0 (`tauri.conf.json`, `Cargo.toml`, `package.json`)                                                                                                               |
| Source       | `cf645d04b16aa4f3d1c5a58cf45b70df29dbf4c9`, clean tree                                                                                                                |
| DMG          | `apps/desktop/src-tauri/target/release/bundle/dmg/Kiko_0.2.0_aarch64.dmg`, 5,308,934 bytes, sha256 `c418fac1416a4a67922608400b2b41e9b44d9862aa10a0d565c845f49b97aea3` |
| App binary   | sha256 `8b8e669128ff07bf426c8f1a0fd3813424da2df103eae721584bb5760bc86475`, bundle 7.4 MB                                                                              |
| Signing      | ad-hoc, hardened runtime; **not** Developer ID signed, **not** notarised                                                                                              |
| Toolchain    | rustc/cargo 1.100.0, Node 26.9.0, pnpm 11.9.0, macOS 27.2                                                                                                             |
| Architecture | Apple Silicon (aarch64), macOS 12+                                                                                                                                    |

Installation (internal testing): open the DMG, drag Kiko to Applications (replaces 0.1.0 — the
Keychain session and server setting are kept), first launch with right-click → Open, then
**Kiko → Server Connection…** → `http://localhost:8000` with the local stack running.

## 23. Operational requirements

PostgreSQL 16, Redis, API, Celery worker, outbox and transactional-email dispatchers, SMTP
provider, Ollama with the model on a private network (≈ 8 GB memory, GPU recommended), HTTPS
reverse proxy, backups (`docs/production-readiness.md`), metrics endpoint with token. Production configuration
now rejects Codex and any non-local AI provider.

## 24. Remaining deployment blockers

1. Production inference host decision (GPU/memory) — Hetzner not assessed or modified.
2. HTTPS staging/production backend URL for the desktop app.
3. Apple Developer ID signing and notarisation.
4. Real SMTP provider configuration.
5. Real-account validation of Gmail/Calendar/GitHub if they are in scope.
6. Owner acceptance of the remaining LOW items (KQA-010, KQA-011) and of AI latency (~45 s per plan
   on the M4).

## 25. Final readiness decision

**READY FOR OWNER ACCEPTANCE TESTING.**

The application is functionally verified on the macOS test machine with real local AI, all
confirmed CRITICAL/HIGH findings are fixed with regression tests, multi-tenant isolation,
authentication, persistence and recovery are verified, and CI is green. It is **not** classified
as ready for deployment preparation because the deployment blockers above depend on owner
decisions and external accounts; nothing was deployed and Hetzner was not touched.

## 26. Addendum — acceptance round (2026-11-20)

Second pass during owner acceptance testing, branch `qa/kiko-acceptance-hardening`, on
macOS 27.2.1 (updated 2026-11-16, after the first pass).

**Temporary accounts.** `kiko-local.sh accounts` created an owner, one account per role (admin,
manager, member, viewer) and a platform administrator in a "Pixart Acceptance" workspace on the
Business plan; credentials only in `~/.kiko-local/test-accounts.txt` (mode 600).

**Results (after fixes)**

| Check                                       | Result                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| Backend tests (SQLite)                      | 291 passed, 6 skipped (integration tests, need their own databases)     |
| Backend tests (PostgreSQL + integration)    | 297/297                                                                 |
| Web (Vitest, typecheck, ESLint, Prettier)   | 64/64, clean                                                            |
| Rust (tests, rustfmt, clippy `-D warnings`) | 21/21, clean                                                            |
| Smoke (`test`)                              | 20/20                                                                   |
| Role sweep (`role-matrix`, new)             | viewer: 76 writes probed, 0 allowed · member/manager: 8/8 admin refused |
| IDOR sweep                                  | 93 operations, 0 cross-tenant leaks                                     |
| AI evaluation (real local model)            | 25/25 · Supervisor p50 54 s, max 111 s (ran alongside other checks)     |
| Performance probe                           | 12/12 · 792 req/s at concurrency 10, p95 17 ms                          |
| Dashboard quality sweep                     | 21 screens × desktop/mobile: no findings                                |
| Desktop journey (real app, local AI)        | all phases passed (after KQA-022)                                       |
| Installed 0.2.1 in /Applications            | cold-start `kiko://verify-email` link verified the account              |

**Defects found and fixed:** KQA-016 (viewers could write — HIGH), KQA-017 (invited members
locked in onboarding — HIGH), KQA-018 (local web dev server, #35), KQA-019 (read-only UX),
KQA-020 (CRM list N+1), KQA-021 (local port), KQA-022 (hidden desktop window suspended by
WebKit — HIGH). Details and regression tests: `KIKO-FULL-DEFECT-REGISTER.md`.

**Decision unchanged:** READY FOR OWNER ACCEPTANCE TESTING, now with Kiko for macOS 0.2.1.
