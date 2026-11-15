# Kiko — Local model inventory

Recorded 2026-11-15 on the macOS test machine (Apple M4, 32 GB unified memory, 460 GB disk with
~78 GB free). Runtime: **Ollama 0.40.16** (Homebrew service `ollama`, listening on
`127.0.0.1:11434`). The Ollama service and its model store (`~/.ollama`) are shared with the Web
Content Flow project on this Mac: Kiko only reads from them through the HTTP API and adds no
models without the owner's authorisation.

## Models

| Tag | Role in Kiko | Family / params | Quantisation / format | Size | Licence | Digest (sha256) |
| --- | --- | --- | --- | --- | --- | --- |
| `gemma4:12b-it-qat` | **Default** for Supervisor, Kiko AI, specialist agents, summarisation (structured JSON via native schema) | gemma4 · 11.9 B · context 262,144 | Q4_0 · GGUF | 7,151,003,754 B (7.2 GB) | Apache-2.0 | `38044be4f923e5a55264ed7df4eaac2676651a905f735197c504045140c02bd3` |
| `qwen3.5:9b` | Evaluated, **not used** (failed schema validation on Supervisor plans) | qwen3_5 · 9.7 B · context 262,144 | nvfp4 · safetensors | 7,639,229,431 B (7.6 GB) | Apache-2.0 | `d63f830f28d515fefea546f213fca7a75e9dd5176ef51a6deabc952d1c99a911` |
| `qwen3.5:4b` | Evaluated, **not used** (failed schema validation; min-spec candidate only) | qwen3_5 · 4.5 B · context 262,144 | nvfp4 · safetensors | 3,973,305,013 B (4.0 GB) | Apache-2.0 | `7f3251fa6878a78a606bcb3c074283306e5ad2ea411a7774a9dd98a4bc7f2d13` |

Origin: the Ollama model registry (`ollama pull <tag>`), pulled on 2026-11-14 for the Web
Content Flow evaluation (`gemma4` manifest refreshed 2026-11-15). Capabilities reported by
`ollama show`: completion, vision, tools and thinking for all three.

Verify on any machine:

```bash
curl -s http://127.0.0.1:11434/api/tags | python3 -c "import json,sys; [print(m['name'], m['digest']) for m in json.load(sys.stdin)['models']]"
ollama show gemma4:12b-it-qat --license | head -3
```

## Capability coverage

| Capability asked by the directive | Status in Kiko | Model |
| --- | --- | --- |
| Conversation | Kiko AI turns are planned by the Supervisor (structured) | `gemma4:12b-it-qat` |
| Reasoning and planning | Supervisor plans, specialist proposals | `gemma4:12b-it-qat` |
| Tool use | Agents propose tool calls as structured actions; the execution engine runs them after policy and approval checks | `gemma4:12b-it-qat` |
| Structured JSON | All AI outputs (runtime-enforced JSON Schema) | `gemma4:12b-it-qat` |
| Classification | Risk levels and agent assignment inside plans | `gemma4:12b-it-qat` |
| Summarisation | `internal.summarize` tool | `gemma4:12b-it-qat` |
| Retrieval (RAG) | Knowledge search uses PostgreSQL full-text search; no embedding model needed today | — |
| Embeddings / reranking | **Not used by any current feature.** Semantic search would be new scope (needs pgvector + an embedding model such as `embeddinggemma`); see the migration document | not installed |
| Vision / document analysis | No current Kiko feature analyses images; `gemma4` supports vision if one is added | (available in `gemma4`) |
| Code | The only coding feature (Codex) is excluded by the policy; a local coding agent is future scope | — |

No model was downloaded for Kiko during this work: the default model was already present.
Adding an embedding model is not required for the current release and was not done.
