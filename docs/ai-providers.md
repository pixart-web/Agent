# AI providers

**Kiko uses local models only.** Every AI feature depends on
`LLMProvider.generate_structured` (`apps/api/app/ai/base.py`); the only runtime adapter is
`OllamaProvider` (`apps/api/app/ai/providers/ollama.py`), which talks to an Ollama server on
loopback or a private network. External inference APIs (OpenAI, Anthropic, Google Gemini and
similar) are not supported: `AI_PROVIDER` accepts only `ollama`, plus `fake`, which automated
tests inject.

Full design: [ai/KIKO-LOCAL-AI-ARCHITECTURE.md](ai/KIKO-LOCAL-AI-ARCHITECTURE.md) · models:
[ai/KIKO-LOCAL-MODEL-INVENTORY.md](ai/KIKO-LOCAL-MODEL-INVENTORY.md) · measurements:
[ai/KIKO-LOCAL-AI-BENCHMARKS.md](ai/KIKO-LOCAL-AI-BENCHMARKS.md) · migration notes:
[ai/KIKO-LOCAL-AI-MIGRATION.md](ai/KIKO-LOCAL-AI-MIGRATION.md).

## Configuration

```env
AI_PROVIDER=ollama
AI_LOCAL_BASE_URL=http://127.0.0.1:11434   # loopback / private hosts only
AI_LOCAL_MODEL=gemma4:12b-it-qat
AI_LOCAL_STRUCTURED_MODE=native_schema     # or "prompted" for models without schema support
AI_LOCAL_THINK=false
AI_LOCAL_KEEP_ALIVE=30m
AI_LOCAL_NUM_CTX=8192
AI_REQUEST_TIMEOUT_SECONDS=180
AI_MAX_RETRIES=2
```

The runtime is optional at start-up: `/health` and non-AI features keep working, and AI calls
return HTTP 503 with "Local AI runtime is not reachable" or "Local AI model … is not
installed". Every answer is validated against the Pydantic response model; invalid answers are
retried with the validation errors fed back to the model. Specialist agents receive a
response schema restricted to the tools they may use, so the runtime enforces valid tool calls.

## Checks

```bash
cd apps/api
python -m app.scripts.test_supervisor_provider        # one Supervisor plan with the local model
../../scripts/local/kiko-local.sh ai-eval              # every AI flow + network egress check
```

Normal tests inject a deterministic fake provider and make no model call.
