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

| #   | Item                                                                                      | Notes                                                                                                                  |
| --- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| B1  | ~~ORM models drift from migrations (KQA-010)~~                                            | Done: models aligned, duplicate constraints dropped (migration `20261120_0036`), fixtures fixed, `alembic check` in CI |
| B2  | ~~Specialist agents can only use tools that need ids when the task text contains ids~~    | Done: read-only lookup round (search, then act on the records found); see the AI architecture doc                      |
| B3  | Codex development integration excluded                                                    | Needs a local coding agent before development tasks can be automated again                                             |
| B4  | Email, Calendar, GitHub integrations untested with real accounts                          | Least-privilege test accounts needed                                                                                   |
| B5  | ~~Projects ↔ tasks association and automations' scheduled runs not exercised end to end~~ | Done: `kiko-local.sh workflows`; scheduled automations now have a scheduler service (KQA-026)                          |
| B6  | ~~Desktop AI timeout client-side only~~                                                   | Done: Supervisor plans and specialist agent runs both run in the background (E1)                                       |

## C. UX improvements

| #   | Item                                                                                                                                                                                                 |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | ~~Show progress while the local model works~~ — done: elapsed time, explanation and "you can leave this page" for Supervisor plans; elapsed time for agent runs                                      |
| C2  | ~~Explain "Local AI runtime is not reachable" with a recovery hint~~ — done: hints for runtime down, model missing, timeout and worker down (`lib/ai-errors.ts`)                                     |
| C3  | ~~Accessibility: keep the Playwright quality sweep in CI~~ — done: CI job "Accessibility and quality sweep" runs it on every dashboard screen (desktop and phone) with PostgreSQL, Redis and Mailpit |
| C4  | Native menu, command palette and save panel need UI automation with Accessibility permission to be regression-tested                                                                                 |
| C5  | ~~Hide or disable create/edit controls per role~~ — done: `CanEdit`/`EditFieldset` on every dashboard screen; settings disabled for non-admins; subscription cancel for owners only                  |
| C6  | ~~Read-only onboarding for invited non-admins~~ — done: "Join <company>" page with the profile read-only                                                                                             |

## D. Performance improvements

| #   | Item                                | Measurement                                                                                                                        |
| --- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| D1  | AI generation latency               | p50 43.5 s, max 75.7 s on M4; a GPU server or a smaller validated model would cut this                                             |
| D2  | ~~AI concurrency~~                  | Done: model work on its own Celery queue (`ai`) with a dedicated single-process worker; add AI workers per inference host to scale |
| D3  | ~~`/crm/contacts` per-row queries~~ | Fixed in the acceptance round (KQA-020): batched loading                                                                           |

## E. Architectural improvements

| #   | Item                                                                                                                                                     | Justification                                                             |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| E1  | ~~Background AI generation with status polling~~ — done for plans (`POST /commands/{id}/supervisor-runs`) and agent runs (`POST /tasks/{id}/agent-runs`) | Both resume after the page is left; abandoned runs are marked `stale_run` |
| E2  | Second runtime adapter (llama.cpp server) for Linux GPU hosts                                                                                            | Parallel slots and grammar control; no domain change needed               |
| E3  | ~~Celery soft time limits locally (`--pool=solo` ignores them)~~                                                                                         | Done: local prefork worker (3 processes) and time limits on AI tasks      |
| E4  | ~~Auth rate limit hit by local test bursts~~ — done: the local environment allows 60/min (`KIKO_LOCAL_AUTH_RATE_LIMIT`); production keeps 10/min         | Limit stays enabled locally so the 429 path is still exercised            |

## F. Future features (not required for the macOS release)

| #   | Item                                                                           |
| --- | ------------------------------------------------------------------------------ |
| F1  | Semantic knowledge search: pgvector + local embedding model (`embeddinggemma`) |
| F2  | Fine-tuning/LoRA on approved plans once an authorised dataset exists           |
| F3  | Vision/document analysis with `gemma4` (already vision-capable)                |
| F4  | Local coding agent to replace Codex                                            |
