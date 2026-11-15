# Kiko — Functional coverage matrix

Snapshot of 2026-11-15, branch `qa/kiko-full-system-hardening`. Inventory: 192 API operations in
27 routers, 47 web/desktop screens, 37 data models, 38 backend test files (293 tests on
PostgreSQL), 19 web test files (64 tests), 21 Rust tests, desktop journey (29 UI steps +
2 Keychain checks), Playwright dashboard sweep (21 screens × desktop/mobile).

Legend — **Verified**: exercised end to end against the real local stack (and/or the real macOS
app) with persisted results checked. **Tested**: automated tests (backend/web/Rust) only.
**Partial**: some paths verified, others only tested or not at all. **External**: needs real
third-party credentials (disabled). **Excluded**: removed by policy. **Not implemented**.

Evidence keys: `smoke` = `kiko-local.sh test` (20 checks) · `persist` = `test-persisted` ·
`desktop` = real-app journey · `ai` = `ai-eval` (25 checks, real local model) · `idor` = IDOR sweep
(93 operations) · `ui` = Playwright quality sweep · `wf` = live workflow checks B/H/L/F ·
`pytest` = backend suite (SQLite + PostgreSQL) · `vitest` · `rust`.

## Identity

| Function                                          | Status   | Evidence                                                                |
| ------------------------------------------------- | -------- | ----------------------------------------------------------------------- |
| Registration                                      | Verified | smoke, desktop, ui                                                      |
| Email verification (Mailpit)                      | Verified | smoke, desktop, deep link (installed app, warm + cold start)            |
| Login / logout                                    | Verified | smoke, desktop (Keychain item created/removed)                          |
| Password reset                                    | Verified | smoke                                                                   |
| Session refresh + rotation                        | Verified | smoke; replay of an old refresh token revokes the family (dynamic test) |
| Session expiry / relaunch restore                 | Verified | desktop (restore from Keychain, last screen)                            |
| Workspace creation / onboarding                   | Verified | smoke, desktop, ui                                                      |
| Invitations (create, email, accept)               | Verified | wf                                                                      |
| Roles / permissions (member cannot invite admins) | Verified | wf, pytest                                                              |
| Workspace switching                               | Tested   | pytest (`test_workspace_settings`, invitations)                         |
| User management (members PATCH/DELETE)            | Partial  | idor (cross-tenant), pytest; no UI automation                           |

## Kiko AI (local model)

| Function                               | Status                      | Evidence                                                      |
| -------------------------------------- | --------------------------- | ------------------------------------------------------------- |
| Conversations / message history        | Verified                    | ai, desktop                                                   |
| Supervisor plan generation             | Verified                    | ai (5 business cases × 4 runs), desktop `local-ai` phase      |
| Plan regeneration with feedback        | Tested                      | pytest (`test_supervisor`)                                    |
| Agent selection / assignment policy    | Verified                    | ai (agents within catalog), pytest                            |
| Specialist agent runs (tool proposals) | Verified                    | ai (valid `crm.list_clients` proposals, `proposed` status)    |
| Tool execution (worker)                | Verified                    | ai (`internal.summarize`), desktop (approved action executed) |
| Approvals                              | Verified                    | desktop, ai                                                   |
| Prompt-injection resistance            | Verified (defence in depth) | ai injection case; risk policy + approval gates               |
| Provider availability / errors         | Verified                    | runtime-down test (503 message), unit tests                   |
| Execution monitoring                   | Verified                    | desktop (executions list), ui                                 |

## Operations

| Function                           | Status                                                 | Evidence                                                    |
| ---------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------- |
| Commands                           | Verified                                               | desktop, ai, perf                                           |
| Tasks (create, transition, reopen) | Verified                                               | desktop                                                     |
| Projects                           | Verified (create/persist) / Partial (task association) | desktop; association only in pytest                         |
| Agents catalog / configuration     | Tested                                                 | pytest; ui renders                                          |
| Execution engine / history         | Verified                                               | desktop, ai                                                 |
| Outbox dispatcher                  | Verified                                               | desktop/ai executions; survives DB outage (KQA-014)         |
| Celery worker                      | Verified                                               | smoke (tasks registered), ai, desktop                       |
| Idempotency / retries              | Tested                                                 | pytest (`test_execution_engine`, integration on PostgreSQL) |

## Business

| Function                                            | Status              | Evidence                                                       |
| --------------------------------------------------- | ------------------- | -------------------------------------------------------------- |
| CRM contacts                                        | Verified            | desktop, perf                                                  |
| Organisations / clients / opportunities / pipelines | Partial             | created live (idor), pytest; no UI automation                  |
| CRM export                                          | Verified (HTTP 200) | wf                                                             |
| Marketing campaigns / content                       | Partial             | created live (idor), pytest                                    |
| Automations                                         | Partial             | created live (idor), pytest; scheduled runs not exercised live |
| Knowledge (upload, approve, full-text search)       | Verified            | wf (TXT on PostgreSQL FTS), pytest (PDF/DOCX limits)           |
| Notifications                                       | Verified            | desktop (events during approvals; no freeze after #33 fix)     |
| Analytics                                           | Tested              | ui renders without errors; pytest                              |
| Settings                                            | Tested              | ui, pytest                                                     |
| Subscription entitlements                           | Partial             | wf (trial subscription read), pytest (`test_commercial`)       |
| Data portability / retention                        | Tested              | pytest                                                         |

## Integrations

| Integration                | Status                                              |
| -------------------------- | --------------------------------------------------- |
| Email (Gmail)              | External — disabled, needs Google OAuth credentials |
| Calendar (Google)          | External — disabled                                 |
| GitHub                     | External — disabled, needs a token                  |
| Codex                      | **Excluded** (external inference, local-AI policy)  |
| External AI providers      | **Excluded** (OpenAI removed)                       |
| Local AI (Ollama)          | Verified (ai, desktop)                              |
| Transactional email (SMTP) | Verified with Mailpit; real SMTP not tested         |

## macOS application

| Function                                                  | Status              | Evidence                                                            |
| --------------------------------------------------------- | ------------------- | ------------------------------------------------------------------- |
| First launch / sign-in                                    | Verified            | desktop                                                             |
| Server configuration (`server.json`)                      | Verified            | installed app uses the stored `http://localhost:8000`               |
| Keychain session storage                                  | Verified            | desktop                                                             |
| Restart / session recovery / last screen                  | Verified            | desktop                                                             |
| Logout                                                    | Verified            | desktop                                                             |
| Deep links (verify-email)                                 | Verified            | installed app warm; release 0.2.0 build cold start (see QA report)  |
| Native notifications                                      | Verified indirectly | no freeze across journeys (fix #33); banners not inspected visually |
| Command palette / shortcuts / file dialogs / native menus | Not automated       | needs Accessibility-permitted UI automation (not available)         |
| Offline state                                             | Tested              | vitest (connection error), previous session's manual check          |
| Release build                                             | Verified            | 0.2.0 built from a clean commit; launched against the local API     |
| Installation into /Applications                           | Not done            | owner approval required to replace the installed app                |
