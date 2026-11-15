# Kiko — Migration to local AI

Date: 2026-11-15 · Branch: `qa/kiko-full-system-hardening` · Owner directive: all Kiko AI runs
on models executed on Pixart-controlled infrastructure; no external inference APIs in
development, tests or production.

## 1. Audit (before)

| Item | Finding |
| --- | --- |
| Providers | `OpenAIProvider` (Responses API structured outputs) — the only real runtime; `fake` for tests |
| External calls | `openai` SDK from the API process and Celery worker; OpenAI Codex CLI from the worker |
| SDKs / packages | `openai>=2.8` (Python), `@openai/codex` (npm, installed in the API image) |
| Features depending on AI | Supervisor plans, Kiko AI conversations (via Supervisor), specialist agents, `internal.summarize`, automation planning |
| Features depending on external inference besides OpenAI SDK | Codex development integration |
| Retrieval | PostgreSQL full-text search — no embedding provider |
| Desktop | no direct AI calls; goes through the API |
| Status without a key | every AI flow → 503 "OpenAI is not configured" |

## 2. What changed

| Area | Change |
| --- | --- |
| Provider | `OllamaProvider` implements the unchanged `LLMProvider` protocol (no domain changes) |
| Configuration | `AI_PROVIDER` ∈ {`ollama`, `fake`}; new `AI_LOCAL_*` settings; `AI_LOCAL_BASE_URL` must be loopback/private; `AI_REQUEST_TIMEOUT_SECONDS` default 60 → 180 |
| Removed | `OpenAIProvider`, `openai` dependency, `OPENAI_*` settings, Codex CLI from the image |
| Codex | CLI never launches; rejected in production configuration |
| Agents | tool-constrained response schema; id-requiring tools only when the task has ids; placeholder-id rejection; repair round with validation feedback; compact tool field list in the prompt |
| Desktop | 600 s timeout for AI generation endpoints |
| Status surfaces | agent overview and platform admin report the local runtime/model health |
| Tests | provider/endpoint-policy unit tests, agent repair tests; real-model `ai-eval`; desktop journey `local-ai` phase |
| Local environment | `kiko-local.sh` uses the Mac's Ollama service with `gemma4:12b-it-qat` |

The migration is complete for every AI flow the product has: each one was exercised with the
real local model (see [benchmarks](KIKO-LOCAL-AI-BENCHMARKS.md), 25/25 checks).

## 3. Runtime choice

| Runtime | Strengths | Gaps for Kiko today | Decision |
| --- | --- | --- | --- |
| **Ollama** | already installed and maintained on the test Mac (shared Homebrew service); Metal acceleration; model registry with digests; JSON-Schema `format` (enforced for gemma4); stable HTTP API; Linux/NVIDIA builds for servers | one generation at a time per model by default; schema enforcement not available for every model (qwen3.5) | **Selected** |
| llama.cpp `llama-server` | fine-grained control, GBNF grammars, OpenAI-compatible local endpoint, parallel slots | separate model management, not installed | Possible second adapter for servers |
| MLX (`mlx_lm.server`) | fastest path on Apple Silicon for some models | macOS-only (no Linux server story), not installed, structured output less mature | Not selected |

Adding another runtime = one new adapter class + a factory branch; no domain changes.

## 4. Skills and tools

Models never execute anything. They return validated proposals; the execution engine runs
registered tools with per-tool risk, approval requirement, input/output schemas, timeouts and
retries, and records audit events. Under the local model this was re-verified with real output:
external-effect actions wait for approval, a prompt-injection command executed nothing, and
agent tool calls are restricted (by schema) to the agent's allowlist. No skill installs
software or runs commands; the only command-running integration (Codex) is excluded.

## 5. Pixart's own models (assessment)

Following the directive's priority order:

1. **Prompt and tool engineering** — done in this migration (constrained schemas made agents
   reliable; no training needed).
2. **RAG and local memory** — current knowledge retrieval is PostgreSQL full-text search with
   approval/sensitivity scoping. Semantic retrieval would add `pgvector` and a local embedding
   model (e.g. `embeddinggemma`, ~0.6 GB). Requirements: pgvector extension on the production
   PostgreSQL, an embeddings column + index migration, a backfill job. Not required for the
   current release; proposed as the next AI step.
3. **Adapting open models** (LoRA on business data) — only once Pixart has an authorised,
   labelled dataset of plans/approvals; the approval history Kiko already stores is the natural
   source. Needs a GPU (a 12B LoRA is impractical on a 32 GB Mac).
4. **Fine-tuning / 5. distillation / 6. training from scratch** — no technical or economic
   justification today. Nothing was trained and no large download was made.

## 6. Production {#production}

Not deployed; nothing was installed on Hetzner. What the production host needs:

| Resource | Minimum for `gemma4:12b-it-qat` | Notes |
| --- | --- | --- |
| Memory for the model | ~8 GB (measured RSS 7.96 GB at 8k context) | more with larger contexts or concurrent models |
| Accelerator | GPU with ≥ 12 GB VRAM recommended (e.g. NVIDIA L4 / RTX 4000 Ada class) | CPU-only inference works but is several times slower than the M4 (expect minutes per plan) |
| CPU / RAM for Kiko | unchanged (API ~150 MB, worker ~90 MB per process) | |
| Disk | 8 GB per model + headroom | store `~/.ollama` on persistent storage |
| Concurrency | one generation at a time per model by default (`OLLAMA_NUM_PARALLEL` raises it at the cost of memory) | AI requests queue; size for peak plans/minute |
| Network | Ollama on a private network or loopback only; never public; authenticate any proxy | `AI_LOCAL_BASE_URL` validation enforces private hosts |
| Isolation | a dedicated inference host or GPU per product avoids one Pixart product starving another | Web Content Flow already uses the same runtime on the Mac |

Open questions for the owner: whether the current Hetzner server has a GPU (do not assume),
whether a dedicated GPU server is acceptable, and how many concurrent users must get AI answers
within a target latency. The macOS edition can run the model on the user's own Mac (32 GB
recommended).

## 7. Rollback

There is no rollback to an external provider (it is no longer allowed). Operational fallbacks:
if the runtime is down, AI features return 503 with a clear message and everything else keeps
working; the model can be switched with `AI_LOCAL_MODEL` (and `AI_LOCAL_STRUCTURED_MODE`) without
code changes.
