# Kiko — Product improvement backlog

From the 2026-11-15 QA program. Fixing existing behaviour was prioritised over new scope;
items below are what remains, ordered by priority inside each section. IDs refer to the
defect register where one exists.

## A. Release blockers

| #   | Item                                                 | Why it blocks                                                                                                                                  | Owner action                                                                       |
| --- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| A1  | Production AI capacity                               | The production host must run the local model (≈ 8 GB, GPU recommended); the current Hetzner server's capability is unknown and was not touched | Decide on the inference host (see `docs/ai/KIKO-LOCAL-AI-MIGRATION.md#production`) |
| A2  | Staging/production HTTPS backend for the desktop app | The app only allows plain HTTP for loopback                                                                                                    | Provide a staging URL                                                              |
| A3  | Apple Developer ID signing + notarisation            | Unsigned builds trigger Gatekeeper warnings; not acceptable for customers                                                                      | Apple Developer account and credentials                                            |
| A4  | Real SMTP provider                                   | Only Mailpit was used; verification/reset emails must be delivered for real                                                                    | Choose and configure the provider                                                  |

## B. Functional defects / gaps

| #   | Item                                                                                  | Notes                                                                                                         |
| --- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| B1  | ORM models drift from migrations (KQA-010)                                            | Align `workspace_id` nullability, unique constraints and indexes; fix ~20 fixtures; add `alembic check` to CI |
| B2  | Specialist agents can only use tools that need ids when the task text contains ids    | Safe by design today; a "search then act" two-step loop would let agents act on records they find             |
| B3  | Codex development integration excluded                                                | Needs a local coding agent before development tasks can be automated again                                    |
| B4  | Email, Calendar, GitHub integrations untested with real accounts                      | Least-privilege test accounts needed                                                                          |
| B5  | Projects ↔ tasks association and automations' scheduled runs not exercised end to end | Covered by unit tests only                                                                                    |
| B6  | ~~Desktop AI timeout client-side only~~                                               | Done for Supervisor plans (background runs, E1); specialist agent runs are still synchronous                  |

## C. UX improvements

| #   | Item                                                                                                                                                                                |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | ~~Show progress while the local model works~~ — done: elapsed time, explanation and "you can leave this page" for Supervisor plans; elapsed time for agent runs                     |
| C2  | Explain "Local AI runtime is not reachable" with a recovery hint in the UI (start Ollama / contact admin)                                                                           |
| C3  | Accessibility: keep the Playwright quality sweep in CI so contrast and accessible-name regressions are caught (5 issues fixed in this program)                                      |
| C4  | Native menu, command palette and save panel need UI automation with Accessibility permission to be regression-tested                                                                |
| C5  | ~~Hide or disable create/edit controls per role~~ — done: `CanEdit`/`EditFieldset` on every dashboard screen; settings disabled for non-admins; subscription cancel for owners only |
| C6  | ~~Read-only onboarding for invited non-admins~~ — done: "Join <company>" page with the profile read-only                                                                            |

## D. Performance improvements

| #   | Item                                | Measurement                                                                                             |
| --- | ----------------------------------- | ------------------------------------------------------------------------------------------------------- |
| D1  | AI generation latency               | p50 43.5 s, max 75.7 s on M4; a GPU server or a smaller validated model would cut this                  |
| D2  | AI concurrency                      | Ollama serves one generation per model at a time; queue or `OLLAMA_NUM_PARALLEL` for multi-user servers |
| D3  | ~~`/crm/contacts` per-row queries~~ | Fixed in the acceptance round (KQA-020): batched loading                                                |

## E. Architectural improvements

| #   | Item                                                                                                                                                              | Justification                                                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| E1  | ~~Background Supervisor generation with status polling~~ — done (`POST /commands/{id}/supervisor-runs` + Celery worker); specialist agent runs remain synchronous | Same pattern can be applied to `run-agent` when needed                                                          |
| E2  | Second runtime adapter (llama.cpp server) for Linux GPU hosts                                                                                                     | Parallel slots and grammar control; no domain change needed                                                     |
| E3  | Celery soft time limits locally (`--pool=solo` ignores them)                                                                                                      | Production prefork on Linux is unaffected; document or use threads pool locally                                 |
| E4  | Auth rate limit is per IP and shared by all auth actions                                                                                                          | Correct for production; makes automated test bursts hit 429 — use a test-only allowance in CI-like environments |

## F. Future features (not required for the macOS release)

| #   | Item                                                                           |
| --- | ------------------------------------------------------------------------------ |
| F1  | Semantic knowledge search: pgvector + local embedding model (`embeddinggemma`) |
| F2  | Fine-tuning/LoRA on approved plans once an authorised dataset exists           |
| F3  | Vision/document analysis with `gemma4` (already vision-capable)                |
| F4  | Local coding agent to replace Codex                                            |
