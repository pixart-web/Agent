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
| KQA-010 | Data model                               | LOW      | Fixed (B1)                         |
| KQA-011 | Desktop dependencies (Linux-only crates) | LOW      | Accepted                           |
| KQA-012 | Desktop / notifications                  | HIGH     | Fixed in #33 (before this program) |
| KQA-013 | Desktop / deep links                     | MEDIUM   | Fixed in #33 (before this program) |
| KQA-014 | Background dispatchers                   | HIGH     | Fixed                              |
| KQA-015 | Web UI accessibility                     | MEDIUM   | Fixed                              |
| KQA-016 | Authorization / workspace roles          | HIGH     | Fixed (acceptance round)           |
| KQA-017 | Invitations / onboarding                 | HIGH     | Fixed (acceptance round)           |
| KQA-018 | Local environment / web dev server       | MEDIUM   | Fixed in #35                       |
| KQA-019 | Web UI / read-only members               | MEDIUM   | Fixed (acceptance round)           |
| KQA-020 | CRM contacts list performance            | LOW      | Fixed (acceptance round)           |
| KQA-021 | Local environment / port conflicts       | LOW      | Fixed (acceptance round)           |
| KQA-022 | Desktop / hidden window suspended        | HIGH     | Fixed (acceptance round)           |
| KQA-023 | Supervisor / abandoned planning runs     | MEDIUM   | Fixed (improvements round)         |
| KQA-024 | Onboarding / phone width overflow        | LOW      | Fixed (improvements round)         |
| KQA-026 | Automations / schedules never ran        | HIGH     | Fixed (roadmap round)              |
| KQA-027 | Local worker / macOS process pool        | MEDIUM   | Fixed (roadmap round)              |
| KQA-028 | Navigation / brand link without a name   | MEDIUM   | Fixed (deep test round 2)          |
| KQA-029 | Module screens / unstyled buttons        | LOW      | Fixed (deep test round 2)          |
| KQA-030 | AI runs / abandoned runs kept 'working'  | MEDIUM   | Fixed (deep test round 2)          |

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

- **Severity:** LOW. **Status:** fixed (B1, 2026-11-20).
- **Description:** `alembic check` on a fresh database reported 16 differences: `workspace_id`
  `NOT NULL` in 9 CRM/marketing/integration tables but nullable in the models; unique
  constraints duplicated by unique indexes (`account_tokens.token_hash`, `workspaces.slug`,
  `codex_runs.task_action_id`); `ix_commands_workspace_created` missing from the model; the
  PostgreSQL full-text index `ix_knowledge_items_fts`.
- **Impact:** production was stricter than the models (safe), but tests built the schema from
  the models and did not enforce those constraints.
- **Fix:** the 9 models declare `workspace_id` required; migration `20261120_0036` drops the
  duplicate constraints and keeps one unique index per column; the model declares the commands
  index; the full-text index is listed as migration-only in `alembic/env.py` (it cannot be
  expressed for the SQLite test schema). 23 test fixtures now set the workspace
  (`tests/workspaces.py`).
- **Regression check:** `alembic check` runs in CI after the migration round trip (job
  "PostgreSQL and Redis integration"); verified locally on a fresh database and on the local
  environment's database.

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

---

## Acceptance round (2026-11-20)

Second pass during owner acceptance testing, with temporary accounts for every role
(`kiko-local.sh accounts`) and a new role sweep (`kiko-local.sh role-matrix`).

### KQA-016 — Viewers could change the workspace

- **Severity:** HIGH (a read-only member could create commands and conversations, which start
  AI work, create projects and milestones, cancel actions and comment on approvals).
- **Reproduction:** `role-matrix` before the fix: viewer, active in the shared workspace →
  12 of 78 write operations answered 2xx (`POST /commands`, `/commands/{id}/cancel|duplicate|restore`,
  `/conversations`, `/conversations/{id}/messages`, `/projects`, `/projects/{id}/milestones`,
  `/actions/{id}/cancel`, `/approvals/{id}/comments`, …).
- **Root cause:** the viewer check existed only in the CRM, marketing, automations, client and
  knowledge routes; every other workspace router accepted any member.
- **Fix:** `require_workspace_editor` (`app/api/dependencies/workspace_role.py`) applied at router
  level to all workspace-scoped routers: writes from a viewer of the active workspace → 403
  "Workspace edit permission is required"; reads unchanged.
- **Regression tests:** `tests/test_workspace_roles.py::test_viewer_is_read_only_and_member_can_edit`
  (fails without the fix: 6× 2xx); live `role-matrix`: viewer 76 writes probed, 0 allowed;
  member and manager refused all workspace administration (8/8).

### KQA-017 — Invited members locked out by the company-setup onboarding

- **Severity:** HIGH (every invited user, of any role, was sent to "Set up your company
  workspace" and could not leave it: saving needs owner/admin rights, so the form failed and the
  dashboard stayed unreachable).
- **Reproduction:** invite a member, accept, sign in on the web → `/onboarding`; submitting returns
  403 and the page stays on onboarding.
- **Root cause:** onboarding completion is per user, but the form always submits the company
  profile, which only managers of the workspace may change; accepting an invitation neither
  completed onboarding nor opened the joined workspace.
- **Fix:** accepting an invitation makes the joined workspace active and completes the invitee's
  onboarding; non-managers may finish onboarding when they resubmit the profile unchanged
  (unblocks members who joined before the fix). Changing the profile still needs owner/admin.
- **Regression tests:** `test_invitee_lands_in_the_team_workspace_without_company_setup`,
  `test_member_can_finish_onboarding_without_changing_the_company`; live: new viewer and manager
  land on `/dashboard`; a previously stuck member finished onboarding from the web.

### KQA-018 — Desktop build broke the local web dev server (fixed in #35)

- **Severity:** MEDIUM (emailed verification links stayed on "Verifying your email…").
- **Root cause / fix:** `next build` for the desktop UI rewrote `.next`, used by `next dev`; the
  local dev server now uses `.next-dev`. Verified by building while the dev server runs.

### KQA-019 — Read-only members saw edit forms and misleading errors

- **Severity:** MEDIUM (UX). A viewer could fill in "New project" and got "The project could not
  be created. Check the details and retry."
- **Fix:** the dashboard navigation shows the active workspace and role, and viewers get a
  read-only notice explaining that edits need an owner or admin. Forms are still shown (the
  server refuses the write); hiding each control per role is listed as an improvement.
- **Verification:** Playwright as viewer (screenshot); quality sweep 21 screens × 2: no findings.

### KQA-020 — CRM contact list ran three queries per contact

- **Severity:** LOW (performance; `/crm/contacts` p50 8.9 ms vs ~2 ms for other lists, 301
  queries for 100 contacts).
- **Fix:** methods, addresses and tags are loaded in three batched queries for the whole page.
- **Regression test:** `tests/test_crm_api.py::test_contact_list_matches_contact_details` (list
  output identical to the per-contact detail).

### KQA-021 — Local PostgreSQL port could not be changed for an existing cluster

- **Severity:** LOW (local environment). Another project's container took port 55432; the port
  was fixed in `postgresql.conf` at cluster creation, so `KIKO_LOCAL_PG_PORT` had no effect.
- **Fix:** `pg_ctl -o "-p $PG_PORT"` and a persistent `~/.kiko-local/ports.env`.

### KQA-022 — Desktop page suspended while Kiko is behind other windows

- **Severity:** HIGH. With the Kiko window hidden or behind other apps, WebKit (macOS 27.2.1,
  installed 2026-11-16) suspends the page after a few seconds: the notification poller stops (no
  native notifications while Kiko is in the background) and a Supervisor plan being generated
  is never shown — the server answers, the page never processes the answer. Found because the
  desktop journey, which runs the window in the background, started to time out in the
  `local-ai` phase (it passed on 2026-11-15, before the OS update).
- **Diagnosis:** the API answered `201` in ~46 s; native threads idle (process sample); a probe
  in the hidden window showed `visibilityState=hidden` and a 25 s `setTimeout` that never fired,
  while a 5 s one did. The same plan generation in the web client showed the plan after 47 s.
- **Fix:** the main window uses `BackgroundThrottlingPolicy::Throttle` (WebKit limits a hidden
  page's work but does not suspend it).
- **Verification:** the hidden-window probe fires the 25 s timer; full desktop journey with the
  real local model passes (see QA report addendum).

## Improvements round (2026-11-20)

### KQA-023 — An abandoned planning run blocked the command forever

- **Severity:** MEDIUM. If the API (or, with background planning, the worker) stopped during a
  Supervisor generation, the run stayed `running` and every later attempt answered "Supervisor
  planning is already in progress".
- **Fix:** runs still active after the model's whole time budget plus 2 minutes are marked
  failed (`stale_run`) before a new run starts.
- **Regression test:** `tests/test_supervisor_background.py::test_a_run_abandoned_by_a_dead_process_no_longer_blocks_planning`.

### KQA-024 — Onboarding card wider than a phone screen with long company names

- **Severity:** LOW. A long word in the large title forced the card past 390 px.
- **Fix:** the card can shrink and the title wraps. Verified at 390 px: no horizontal overflow.

## Background agents round (2026-11-20)

### KQA-025 — An abandoned agent run blocked its task forever

- **Severity:** MEDIUM. Same cause as KQA-023 for specialist agents: a run left `running` by a
  stopped API or worker made every later attempt answer "An agent run is already active".
- **Fix:** agent runs older than twice the model's time budget plus 2 minutes are marked failed
  (`stale_run`) before a new run starts; the next start counts as a re-run.
- **Regression test:** `tests/test_agent_runs_background.py::test_a_run_abandoned_by_a_dead_worker_no_longer_blocks_the_task`.

## Roadmap round (2026-11-21)

### KQA-026 — Scheduled automations never ran on their own

- **Severity:** HIGH. Schedules were only processed by `python -m app.scripts.run_due_automations`
  run by hand; no service in Docker Compose, production Compose or the local environment called
  it, so a scheduled automation created in the UI never fired.
- **Fix:** `app.scripts.run_automation_scheduler` (resilient loop, every 30 s) and the
  `automation-scheduler` / `scheduler` services.
- **Tests:** `tests/test_automations.py::test_scheduler_loop_runs_due_schedules_until_stopped`;
  live `kiko-local.sh workflows` (the running scheduler fires a due schedule once, creates one
  command and advances the next run).

### KQA-027 — Local worker: every task failed in the macOS process pool

- **Severity:** MEDIUM (local environment only; production runs Linux with fork). Found while
  moving the local worker from `solo` to `prefork`: Python on macOS starts pool processes with
  _spawn_, and Celery's fast trace path then fails every task ("not enough values to unpack").
- **Fix:** `FORKED_BY_MULTIPROCESSING=1` (plus `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`,
  `NO_PROXY=*`) in `kiko-local.sh`. Verified: actions execute in `SpawnPoolWorker` processes and
  the smoke test passes.
- **Side effect cleaned up:** two agent runs started while the pool was broken stay `running`
  until the stale-run cut-off marks them failed.

## Deep test round 2 (2026-11-23)

Fresh temporary accounts (owner, admin, manager, member, viewer, platform administrator) in a
new fictitious workspace; every screen visited as every role; write flows driven through the
UI with the real local model.

### KQA-028 — Navigation brand link had no accessible name on phones and when collapsed

- **Severity:** MEDIUM (WCAG 2.4.4 / 4.1.2, axe "link-name", serious). Introduced with the
  official logo: when only the robot mark shows (collapsed rail, phone width), the mark is
  decorative and the link had no name. Found by the quality sweep on all 21 screens (phone).
- **Fix:** the link is named "Kiko — Início". Sweep clean again on desktop and phone.
- **Prevention:** the quality sweep now runs in CI (C3), so this class of regression fails a PR.

### KQA-029 — Bare buttons in module screens looked like browser defaults

- **Severity:** LOW (visual). Older screens (automations, knowledge, tasks, marketing,
  command list) use `<button>` without a class; on the dark theme they rendered as flat grey
  system buttons (e.g. "Create automation").
- **Fix:** base Kiko styles for unclassed buttons in the app (form submit = primary amber,
  others secondary) and consistent sizing for unclassed selects.

### KQA-030 — Abandoned AI runs kept showing "working…"

- **Severity:** MEDIUM. A plan or agent run left `running` by a dead worker was only failed
  when someone started another run on the same command/task; until then the screen showed
  progress forever (two such runs from 21 Nov were still `running` on 23 Nov).
- **Fix:** `app.services.run_maintenance.fail_abandoned_runs`, called by the automation
  scheduler every 30 s; audited; the command returns to pending when no plan was stored.
  Verified live: the two old runs were failed within seconds of the scheduler restart.
- **Tests:** `tests/test_run_maintenance.py`.
