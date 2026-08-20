# AI providers

The Supervisor depends on `LLMProvider.generate_structured`. Provider adapters return a
typed `LLMResult` containing validated data and optional model, token, request, cost,
and latency metadata. Domain services do not import provider SDK details.

## OpenAI

The initial adapter uses the official Python SDK Responses API structured-output parser
with the Pydantic proposal schema. It does not extract JSON from markdown. Configure:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
AI_REQUEST_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=2
```

The key is optional at process startup so `/health` and non-AI features keep working.
Invoking generation without it returns a safe configuration error. Never commit or log
the key. `OPENAI_MODEL` must identify a structured-output-capable model available to the
account.

Timeout is passed to the SDK client. SDK retries are disabled; the adapter alone owns a
bounded exponential retry for timeouts, connection/rate-limit/server errors, and a
missing structured result. Permanent configuration and client request errors do not
retry. Normal tests inject a deterministic fake provider, and CI sets
`AI_PROVIDER=fake`; neither makes an external request.

An optional manual check is available:

```bash
cd apps/api
python -m app.scripts.test_supervisor_provider
```

It skips when `OPENAI_API_KEY` is absent and prints only validation and safe metadata.
Provider output and commands are not persisted raw. Adding Anthropic or a local adapter
should implement the same protocol and be selected in the factory without changing the
Supervisor domain.

Reference: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
