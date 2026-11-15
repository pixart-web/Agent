"""Local AI provider (Ollama) and the local-only AI configuration policy.

All HTTP is served by httpx.MockTransport: deterministic, no runtime or network needed.
Real-model behaviour is covered by tests/local_ai (opt-in, see docs/ai).
"""

import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.exceptions import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.ai.provider_factory import build_local_provider, get_llm_provider
from app.ai.providers.ollama import OllamaProvider
from app.core.config import Settings
from app.core.network import is_private_endpoint
from app.schemas.supervisor import SupervisorPlanProposal

SECRET = "test-only-auth-secret-with-at-least-32-characters"


def plan_json(**overrides: object) -> str:
    value: dict[str, object] = {
        "title": "Acquisition plan",
        "objective": "Generate qualified leads",
        "reasoning_summary": "Separate research from outreach preparation.",
        "tasks": [
            {
                "agent_id": "marketing",
                "title": "Research the market",
                "instructions": "Prepare an internal market brief.",
                "priority": "high",
                "risk_level": "green",
                "sequence": 1,
            }
        ],
    }
    value.update(overrides)
    return json.dumps(value)


def chat_reply(content: str, prompt: int = 120, output: int = 60) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "message": {"role": "assistant", "content": content},
            "prompt_eval_count": prompt,
            "eval_count": output,
        },
    )


def provider(handler, **kwargs: object) -> tuple[OllamaProvider, list[dict]]:
    requests: list[dict] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append({"url": str(request.url), "body": json.loads(request.content or b"{}")})
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    options: dict[str, object] = {
        "base_url": "http://127.0.0.1:11434",
        "model": "gemma4:12b-it-qat",
        "timeout_seconds": 5,
        "max_retries": 1,
        "sleep": lambda _seconds: None,
        "client": client,
    }
    options.update(kwargs)
    return OllamaProvider(**options), requests


def generate(instance: OllamaProvider):
    return instance.generate_structured(
        system_prompt="system rules",
        user_prompt="user command",
        response_model=SupervisorPlanProposal,
    )


def test_native_schema_request_and_validated_result() -> None:
    instance, requests = provider(lambda _r: chat_reply(plan_json()))
    result = generate(instance)

    assert result.data.tasks[0].agent_id == "marketing"
    assert (result.provider, result.model) == ("ollama", "gemma4:12b-it-qat")
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (120, 60, 180)
    assert result.estimated_cost is None
    sent = requests[0]
    assert sent["url"] == "http://127.0.0.1:11434/api/chat"
    body = sent["body"]
    assert body["model"] == "gemma4:12b-it-qat"
    assert body["stream"] is False and body["think"] is False
    assert body["format"] == SupervisorPlanProposal.model_json_schema()
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"].startswith("system rules")
    assert body["messages"][1] == {"role": "user", "content": "user command"}


def test_prompted_mode_embeds_schema_and_strips_code_fences() -> None:
    fenced = f"```json\n{plan_json()}\n```"
    instance, requests = provider(lambda _r: chat_reply(fenced), structured_mode="prompted")
    result = generate(instance)

    assert result.data.title == "Acquisition plan"
    body = requests[0]["body"]
    assert "format" not in body
    assert '"tasks"' in body["messages"][0]["content"]


def test_invalid_answer_is_repaired_with_validation_feedback() -> None:
    replies = iter([chat_reply('{"title": "x"}'), chat_reply(plan_json())])
    instance, requests = provider(lambda _r: next(replies))
    result = generate(instance)

    assert result.data.objective == "Generate qualified leads"
    repair_messages = requests[1]["body"]["messages"]
    assert repair_messages[-2]["role"] == "assistant"
    assert "did not match the required JSON schema" in repair_messages[-1]["content"]
    assert result.total_tokens == 360


def test_invalid_answer_after_all_attempts_raises() -> None:
    instance, _ = provider(lambda _r: chat_reply("not json at all"))
    with pytest.raises(AIInvalidResponseError):
        generate(instance)


def test_empty_content_is_invalid() -> None:
    instance, _ = provider(lambda _r: chat_reply("   "), max_retries=0)
    with pytest.raises(AIInvalidResponseError):
        generate(instance)


def test_runtime_down_is_unavailable_after_retry() -> None:
    calls = []

    def down(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("refused", request=request)

    instance, _ = provider(down)
    with pytest.raises(AIProviderUnavailableError, match="not reachable"):
        generate(instance)
    assert len(calls) == 2


def test_timeout_then_success_retries_with_backoff() -> None:
    sleeps: list[float] = []
    replies = iter(["timeout", "ok"])

    def flaky(request: httpx.Request) -> httpx.Response:
        if next(replies) == "timeout":
            raise httpx.ReadTimeout("slow", request=request)
        return chat_reply(plan_json())

    instance, _ = provider(flaky, sleep=sleeps.append)
    assert generate(instance).data.tasks
    assert sleeps == [0.5]


def test_timeout_on_every_attempt_raises_timeout() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    instance, _ = provider(slow)
    with pytest.raises(AIProviderTimeoutError):
        generate(instance)


def test_missing_model_is_a_configuration_error_without_retry() -> None:
    calls = []

    def missing(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404, json={"error": "model not found"})

    instance, _ = provider(missing)
    with pytest.raises(AIConfigurationError, match="not installed"):
        generate(instance)
    assert len(calls) == 1


def test_runtime_server_error_is_unavailable() -> None:
    instance, _ = provider(lambda _r: httpx.Response(500, text="boom"))
    with pytest.raises(AIProviderUnavailableError):
        generate(instance)


def test_health_reports_runtime_and_model() -> None:
    tags = {"models": [{"name": "gemma4:12b-it-qat"}]}
    instance, _ = provider(lambda _r: httpx.Response(200, json=tags))
    assert instance.health() == {"reachable": True, "model_installed": True}

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    offline, _ = provider(down)
    assert offline.health() == {"reachable": False, "model_installed": False}


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "http://10.0.4.2:11434",
        "http://192.168.1.20:11434",
        "http://172.20.0.5:11434",
        "http://ollama:11434",
        "https://ai.pixart.internal",
        "http://gpu-01.local:11434",
    ],
)
def test_private_ai_endpoints_are_accepted(url: str) -> None:
    assert is_private_endpoint(url)
    assert Settings(auth_secret_key=SECRET, ai_local_base_url=url).ai_local_base_url


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "https://api.anthropic.com",
        "https://generativelanguage.googleapis.com",
        "http://8.8.8.8:11434",
        "https://ollama.example.com",
        "http://user:pass@127.0.0.1:11434",
        "ftp://127.0.0.1",
        "not a url",
    ],
)
def test_public_or_invalid_ai_endpoints_are_rejected(url: str) -> None:
    assert not is_private_endpoint(url)
    with pytest.raises(ValidationError, match="AI_LOCAL_BASE_URL"):
        Settings(auth_secret_key=SECRET, ai_local_base_url=url)


@pytest.mark.parametrize("value", ["openai", "anthropic", "gemini"])
def test_external_ai_providers_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="local AI only"):
        Settings(auth_secret_key=SECRET, ai_provider=value)


def test_factory_builds_local_provider_from_settings() -> None:
    settings = Settings(
        auth_secret_key=SECRET,
        ai_local_model="qwen3.5:9b",
        ai_local_structured_mode="prompted",
        ai_request_timeout_seconds=90,
    )
    built = build_local_provider(settings)
    assert (built.model_name, built.structured_mode, built.timeout_seconds) == (
        "qwen3.5:9b",
        "prompted",
        90,
    )


def test_fake_provider_is_never_built_by_the_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ai import provider_factory

    monkeypatch.setattr(
        provider_factory,
        "get_settings",
        lambda: Settings(auth_secret_key=SECRET, ai_provider="fake"),
    )
    with pytest.raises(AIConfigurationError):
        get_llm_provider()
