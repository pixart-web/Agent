# Kiko — Local AI architecture

**Policy (mandatory):** every Kiko AI feature runs on models executed on infrastructure Pixart
controls. Kiko does not call external inference APIs (OpenAI, Anthropic, Google Gemini or
similar) in development, tests or production. Model weights may be downloaded once from
authorised open-model registries; inference never leaves the machine or the private network.

Status: implemented on branch `qa/kiko-full-system-hardening` (2026-11-15). Validated on the
macOS test machine (Apple M4, 32 GB). See [benchmarks](KIKO-LOCAL-AI-BENCHMARKS.md),
[model inventory](KIKO-LOCAL-MODEL-INVENTORY.md) and [migration](KIKO-LOCAL-AI-MIGRATION.md).

## 1. Where AI is used in Kiko

Every AI call goes through one domain interface, `LLMProvider.generate_structured`
(`apps/api/app/ai/base.py`): a system prompt, a user prompt and a Pydantic response model in, a
validated object plus usage metadata out. Consumers:

| Feature                                                                           | Code                                            | Response model           | Runs in       |
| --------------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------ | ------------- |
| Supervisor plan generation / regeneration                                         | `services/supervisor_service.py`                | `SupervisorPlanProposal` | API request   |
| Kiko AI conversations (each message becomes a command, planned by the Supervisor) | `services/conversation_service.py` + Supervisor | `SupervisorPlanProposal` | API request   |
| Specialist agents (marketing, sales, support, development)                        | `agents/runner.py`, `agents/specialists/*`      | `AgentProposal`          | API request   |
| `internal.summarize` tool                                                         | `execution/tools/internal.py`                   | `SummarizeOutput`        | Celery worker |
| Automation planning                                                               | `automations/tasks.py`                          | `SupervisorPlanProposal` | Celery worker |

Knowledge retrieval uses PostgreSQL full-text search (`to_tsvector`), not embeddings, so it
already works without any model.

## 2. Components

```
 Kiko for macOS / web client
            │  HTTPS (or loopback HTTP in development)
            ▼
 FastAPI ── LLMProvider protocol ── OllamaProvider ──HTTP──▶ Ollama runtime ──▶ local model
 Celery worker ───────────┘          (app/ai/providers/      127.0.0.1:11434     (gemma4:12b-it-qat)
                                       ollama.py)            or private network
```

- **Abstraction:** domain modules depend only on `LLMProvider`; the runtime adapter is chosen
  in `app/ai/provider_factory.py`. Another runtime (llama.cpp server, MLX server) can be added
  as a new adapter without touching the Supervisor, agents or tools.
- **Runtime:** Ollama (0.40.16 on the test Mac, Homebrew service). Chosen because it is already
  installed and maintained on this machine, serves GGUF and MLX-backed models on Apple Silicon
  through Metal, enforces JSON Schemas for models that support it, and has a stable local HTTP
  API. llama.cpp (`llama-server`) and MLX (`mlx_lm.server`) were assessed as alternatives: both
  are viable adapters later, but neither adds a capability Kiko needs today and neither is
  installed (see the migration document for the comparison).
- **Model:** `gemma4:12b-it-qat` (Apache-2.0, 11.9 B parameters, Q4_0, 7.2 GB). The only model
  on this machine that produced schema-valid Supervisor plans on every attempt (see benchmarks).

## 3. The local provider (`OllamaProvider`)

- `POST {AI_LOCAL_BASE_URL}/api/chat` with `stream: false`, `think: false` (thinking spends the
  output budget before the JSON), `keep_alive` (model stays loaded, default 30 min) and
  `num_ctx` (default 8192).
- **Structured output:** `native_schema` sends the response model's JSON Schema as Ollama's
  `format`, so the runtime constrains generation; `prompted` puts the schema in the instructions
  and strips code fences, for models whose runtime cannot enforce schemas (qwen3.5).
- **Validation and repair:** the answer is always validated with the response model; on
  failure the validation errors are sent back once per retry so the model can correct itself.
- **Errors:** runtime down → `AIProviderUnavailableError` ("Local AI runtime is not
  reachable"), timeout → `AIProviderTimeoutError`, model missing (HTTP 404) →
  `AIConfigurationError` ("Local AI model … is not installed", not retried). The API maps these
  to HTTP 503 with that message; the UI shows it.
- **Usage:** prompt and output token counts from the runtime are stored on Supervisor and agent
  runs; `estimated_cost` is empty (no per-call cost).
- **No proxies:** the HTTP client ignores system proxy variables (`trust_env=False`).

## 4. Network boundary

- `AI_PROVIDER` accepts only `ollama` (or `fake`, injected by automated tests). Any other value,
  e.g. `openai`, fails at start-up with "Kiko uses local AI only".
- `AI_LOCAL_BASE_URL` must be loopback, a private/link-local address, a single-label service
  name (e.g. `ollama` in Docker) or a private DNS suffix (`.internal`, `.local`, `.lan`,
  `.home.arpa`, `.localhost`); public hosts such as `api.openai.com` are rejected
  (`app/core/network.py`, tests in `tests/test_ai_provider.py`).
- The `openai` Python SDK was removed from the API dependencies and the OpenAI Codex CLI from
  the API image.
- **Codex integration** (OpenAI Codex CLI) is excluded: the CLI adapter refuses to start
  ("disabled by the local-AI policy") and production configuration rejects
  `CODEX_INTEGRATION_ENABLED=true`. The sandboxing code is kept for a future local coding agent.
- Verified empirically: during the full local-AI evaluation every TCP connection of the API,
  the Celery worker and Ollama was sampled once per second — all were loopback.
- Ollama listens on `127.0.0.1` by default. It must never be exposed publicly; on a server use
  a private network or a reverse proxy with authentication.

## 5. Desktop app timing

Local generation takes about 45–60 s on the M4. The desktop app's API proxy allows 600 s for
the four AI generation endpoints (`generate-plan`, `regenerate-plan`, `run-agent`,
`rerun-agent`) and keeps 30 s for everything else (`apps/desktop/src-tauri/src/api.rs`). The
backend bounds each model call with `AI_REQUEST_TIMEOUT_SECONDS` (default 180).

### Background planning

Supervisor plans run in the background. `POST /commands/{id}/supervisor-runs` opens a
`running` run and answers `202` at once; the Celery worker
(`app.services.supervisor_tasks.complete_supervisor_run`) calls the model and stores the
draft plan or marks the run failed with its reason. Clients poll
`GET /commands/{id}/supervisor-runs` (every 2.5 s in the web and desktop UI), show elapsed
time, and resume following the run when the page is opened again. With `feedback` in the
body the current draft plan is revised. A run still active after the model's whole time
budget (`AI_REQUEST_TIMEOUT_SECONDS × (AI_MAX_RETRIES + 1)` + 2 min) is marked `stale_run`
so a dead worker never blocks planning. The synchronous `generate-plan`/`regenerate-plan`
endpoints remain for API clients.

Specialist agent runs follow the same pattern: `POST /tasks/{id}/agent-runs` (optional
`feedback`; a task that already ran is re-run, keeping the history) answers `202` with the
running run, the worker task `app.services.agent_run_tasks.complete_agent_run` stores the
proposed actions, and clients poll `GET /tasks/{id}/agent-runs`. Agent runs may call the
model twice (one repair round), so their stale limit is twice the planning budget. The
synchronous `run-agent`/`rerun-agent` endpoints remain for API clients.

Known local AI failures (runtime not reachable, model not installed, timeout, worker not
answering) are shown in the web and desktop UI with a recovery hint (`lib/ai-errors.ts`).

On a single local worker (`--pool=solo`) a plan generation occupies the worker for about a
minute; production workers run with concurrency.

## 6. Configuration

| Variable                     | Default                  | Meaning                                 |
| ---------------------------- | ------------------------ | --------------------------------------- |
| `AI_PROVIDER`                | `ollama`                 | `ollama` or `fake` (tests only)         |
| `AI_LOCAL_BASE_URL`          | `http://127.0.0.1:11434` | Ollama endpoint (loopback/private only) |
| `AI_LOCAL_MODEL`             | `gemma4:12b-it-qat`      | Model tag                               |
| `AI_LOCAL_STRUCTURED_MODE`   | `native_schema`          | `native_schema` or `prompted`           |
| `AI_LOCAL_THINK`             | `false`                  | Enable model thinking                   |
| `AI_LOCAL_KEEP_ALIVE`        | `30m`                    | How long the model stays loaded         |
| `AI_LOCAL_NUM_CTX`           | `8192`                   | Context window                          |
| `AI_REQUEST_TIMEOUT_SECONDS` | `180`                    | Per-call timeout                        |
| `AI_MAX_RETRIES`             | `2`                      | Retries (with repair feedback)          |

## 7. Skills, tools and approvals

Models never execute anything themselves. They return proposals (plans, actions) validated
against Pydantic schemas; tools run only through the existing execution engine, whose
registry declares per-tool risk, approval requirements, input/output schemas, timeouts and
retries. External-effect tools require human approval; plans require human approval before
tasks run. The local migration does not change these controls, and the evaluation verified
them with real model output (external communication flagged for approval, an injection
attempt produced no executed action).

## 8. Production (Pixart infrastructure)

Not deployed. Requirements and the open questions for the server are in
[KIKO-LOCAL-AI-MIGRATION.md](KIKO-LOCAL-AI-MIGRATION.md#production). Nothing was installed on
Hetzner.
