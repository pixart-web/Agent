# Kiko — Full defect register

Program: `qa/kiko-full-system-hardening` (started 2026-11-15 from `main` @ `f9e1945`).
Severity scale: BLOCKER · CRITICAL · HIGH · MEDIUM · LOW · IMPROVEMENT. Historical findings stay
listed after they are fixed. "Fix commit" refers to commits on the QA branch unless stated.

| ID      | Module                                   | Severity | Status                             |
| ------- | ---------------------------------------- | -------- | ---------------------------------- |
| KQA-001 | AI / architecture                        | BLOCKER  | Fixed                              |
| KQA-002 | Integrations / Codex                     | HIGH     | Fixed (excluded)                   |
| KQA-003 | Web dependencies (Next.js)               | CRITICAL | Fixed                              |
| KQA-004 | Desktop / API proxy                      | HIGH     | Fixed                              |
| KQA-005 | Specialist agents                        | HIGH     | Fixed                              |
| KQA-006 | Test infrastructure                      | MEDIUM   | Fixed                              |
| KQA-007 | Test infrastructure / CI                 | MEDIUM   | Fixed                              |
| KQA-008 | Local environment script                 | MEDIUM   | Fixed                              |
| KQA-009 | Dev dependencies                         | MEDIUM   | Fixed                              |
| KQA-010 | Data model                               | LOW      | Open (documented)                  |
| KQA-011 | Desktop dependencies (Linux-only crates) | LOW      | Accepted                           |
| KQA-012 | Desktop / notifications                  | HIGH     | Fixed in #33 (before this program) |
| KQA-013 | Desktop / deep links                     | MEDIUM   | Fixed in #33 (before this program) |
| KQA-014 | Background dispatchers                   | HIGH     | Fixed                              |
| KQA-015 | Web UI accessibility                     | MEDIUM   | Fixed                              |

---

### KQA-001 — AI depended on an external inference API (OpenAI)

- **Severity:** BLOCKER (owner directive: local AI only).
- **Description:** every AI feature (Supervisor, Kiko AI, specialist agents, summarisation,
  automation planning) called the OpenAI Responses API through `OpenAIProvider`.
- **Reproduction:** `AI_PROVIDER=openai` was the default; without `OPENAI_API_KEY` every AI flow
  returned 503 "OpenAI is not configured".
- **Expected:** inference only on Pixart-controlled hardware. **Actual:** external API.
- **Root cause:** architecture choice before the local-AI directive.
- **Fix:** `OllamaProvider` behind the unchanged `LLMProvider` protocol; `AI_PROVIDER` accepts only
  `ollama`/`fake`; `AI_LOCAL_BASE_URL` restricted to loopback/private hosts; OpenAI provider and
  SDK removed (commit `9e73c23`).
- **Regression tests:** `tests/test_ai_provider.py` (provider behaviour, endpoint policy, external
  providers rejected); real-model evaluation `scripts/local/kiko-local.sh ai-eval`.
- **Remaining risk:** answer quality depends on the local model; human approval stays mandatory.

### KQA-002 — Codex integration performs external inference

- **Severity:** HIGH (policy). **Status:** fixed by exclusion.
- **Description:** the Codex development integration launches the OpenAI Codex CLI, which runs
  inference on OpenAI servers.
- **Fix:** `CodexCLIAdapter.execute` refuses to start ("disabled by the local-AI policy");
  production configuration rejects `CODEX_INTEGRATION_ENABLED=true`; Codex CLI removed from the
  API image (commit `9e73c23`).
- **Regression tests:** `test_cli_adapter_never_launches_codex_under_local_ai_policy`,
  `test_insecure_production_configuration_is_rejected[codex…]`.
- **Remaining risk:** development-agent code changes are unavailable until a local coding agent
  exists (future scope).

### KQA-003 — Next.js critical advisory (unauthenticated RCE in image optimisation) and DoS

- **Severity:** CRITICAL for the web edition (the desktop app ships a static export without the
  Next server).
- **Reproduction:** `pnpm audit --prod` → `next >=10.0.0 <=15.5.27` critical, `>=13 <=15.5.27`
  high.
- **Fix:** `next`/`eslint-config-next` 15.5.29 (patch release, same major) — commit `9e73c23`.
- **Regression check:** `pnpm audit` → "No known vulnerabilities found"; CI frontend job.

### KQA-004 — Desktop app cut AI generation off after 30 s

- **Severity:** HIGH (every Supervisor plan / agent run from the desktop app would time out with
  local models).
- **Reproduction:** local generation takes 33–60 s (measured); the Rust proxy applied a 30 s
  timeout to every request.
- **Fix:** `request_timeout()` gives the four AI generation endpoints 600 s and keeps 30 s for
  everything else (`apps/desktop/src-tauri/src/api.rs`, commit `9e73c23`).
- **Regression test:** Rust unit test in `api.rs` (`request_timeout` cases).

### KQA-005 — Specialist agents never received tool input schemas

- **Severity:** HIGH (specialist agent runs failed with real models).
- **Reproduction:** approve an AI plan, run the assigned agent with the local model → run
  `failed`, `error_code=ToolInputValidationError` (2/2 runs in the first evaluation).
- **Root cause:** the agent prompt listed only tool names; models had to guess `input_payload`
  fields; any mistake failed the run with no chance to correct it.
- **Fix:** compact per-tool field list (`name*:type`, enums inline) in the agent prompt; one repair
  round that feeds the exact validation error back; validation itself unchanged
  (`agents/runner.py`, `agents/context.py`).
- **Regression tests:** `test_agent_prompt_lists_tool_input_schemas`,
  `test_invalid_tool_input_is_repaired_once_with_validation_feedback`,
  `test_invalid_tool_input_twice_fails_the_run`, `test_forbidden_tool_marks_run_failed` (now
  asserts the repair round explicitly).

### KQA-006 — Backend tests only ran on SQLite without foreign keys

- **Severity:** MEDIUM. **Description:** the suite used in-memory SQLite, which ignores foreign
  keys and lacks PostgreSQL full-text search; one test inserted an action for a non-existent task
  and another asserted the SQLite-only retrieval path.
- **Fix:** `TEST_DATABASE_URL` runs the suite on a disposable PostgreSQL database (name must
  contain "test"); SQLite now enforces foreign keys; the two tests fixed.
- **Evidence:** at the time of the fix 286 passed on PostgreSQL 16 + Redis (0 skipped); final: 293 on PostgreSQL, 287 passed / 6 skipped on SQLite.

### KQA-007 — CI never ran the full suite on PostgreSQL

- **Severity:** MEDIUM. **Fix:** the CI integration job creates `agent_pytest_test` and runs the
  full backend suite on PostgreSQL 16 after the integration tests.

### KQA-008 — `kiko-local.sh` race left the Celery worker on the default broker

- **Severity:** MEDIUM (local environment): background jobs silently never ran.
- **Root cause:** each service rewrote `api.env` with `cat >` while the previous one was still
  sourcing it; the worker read an empty file and fell back to `redis://redis:6379/1`.
- **Fix:** atomic write (temporary file + `mv`); `start worker` now waits for "ready" and fails on
  "Cannot connect".

### KQA-009 — 22 advisories in development tooling

- **Severity:** MEDIUM (dev only: vitest/vite, eslint → brace-expansion, js-yaml, minimatch,
  tinypool). **Fix:** vitest 4.1.12, in-range updates, two pnpm overrides; `pnpm audit` clean;
  64/64 web tests, lint, typecheck and format pass.

### KQA-010 — ORM models drift from the migrated schema

- **Severity:** LOW. **Status:** open, documented.
- **Description:** `alembic check` on a fresh database reports differences: `workspace_id` is
  `NOT NULL` in 9 CRM/marketing/integration tables but nullable in the models; some unique
  constraints/indexes exist only in migrations (e.g. `account_tokens.token_hash`,
  `workspaces.slug`, knowledge FTS index).
- **Impact:** production is stricter than the models (safe); tests build the schema from the
  models, so they do not enforce those constraints. Aligning the models breaks ~20 test fixtures
  that insert rows without a workspace (no application code path does).
- **Recommendation:** align models and fixtures in a dedicated change; add `alembic check` to CI.

### KQA-011 — Unmaintained/unsound crates in the Tauri Linux stack

- **Severity:** LOW (accepted). `cargo audit`: 0 vulnerabilities, 5 warnings (`glib`
  RUSTSEC-2024-0429, `zbus_names`/`zvariant`/`zvariant_derive` unmaintained). These belong to
  the GTK/D-Bus stack, which is not compiled for macOS.

### KQA-012 — Desktop app froze after a native notification (fixed in PR #33)

### KQA-013 — Cold-start `kiko://` deep links ignored (fixed in PR #33)

Kept for history; details in `docs/desktop/KIKO-LOCAL-TEST-ENVIRONMENT.md` §9.

### KQA-014 — Dispatchers died when PostgreSQL restarted

- **Severity:** HIGH (after a database restart no verification or reset email was sent until
  someone restarted the dispatcher; the outbox dispatcher could die the same way and stop all
  background execution).
- **Reproduction:** restart PostgreSQL while the stack runs → `mailer` log ends with
  `psycopg.OperationalError ... Connection refused`, process gone; new registrations get no email.
- **Root cause:** the polling loops had no error handling (the outbox loop only guarded the
  per-event send, not the batch claim).
- **Fix:** shared `run_forever()` loop (`app/scripts/_loop.py`): log, exponential backoff capped at
  30 s, resume; SIGTERM-aware. Commit `950b015`.
- **Regression tests:** `tests/test_dispatcher_loop.py`; live: PostgreSQL stopped for 12 s → both
  dispatchers logged two failures and recovered; smoke test 20/20 afterwards.
- **Remaining risk:** in production the container restart policy was already a second line of
  defence.

### KQA-015 — Accessibility violations on dashboard screens

- **Severity:** MEDIUM. Found by the new Playwright sweep (WCAG 2 A/AA, serious/critical):
  contrast 1.49:1 for labels on the highlighted agent card (`/dashboard`, `/dashboard/agents`);
  `<select>` without accessible name on Executions (3), Email (1), Calendar (2), Knowledge (1);
  action composer select/input unlabeled (found by code scan).
- **Fix:** card label colour; `aria-label` on each control (commit `e9e47d2` and follow-up).
- **Regression test:** `apps/web/e2e/dashboard-quality-sweep.spec.ts` — 21 screens, desktop and
  mobile: no findings.
