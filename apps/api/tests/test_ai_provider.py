from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from app.ai.exceptions import (
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.ai.providers.openai import OpenAIProvider
from app.schemas.supervisor import SupervisorPlanProposal


def proposal() -> SupervisorPlanProposal:
    return SupervisorPlanProposal.model_validate(
        {
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
    )


def test_openai_provider_returns_structured_data_and_usage_metadata() -> None:
    response = SimpleNamespace(
        output_parsed=proposal(),
        usage=SimpleNamespace(input_tokens=100, output_tokens=40, total_tokens=140),
        _request_id="req_safe_id",
    )
    client = MagicMock()
    client.responses.parse.return_value = response
    provider = OpenAIProvider(
        api_key=None,
        model="test-model",
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=SupervisorPlanProposal,
    )

    assert result.data == response.output_parsed
    assert result.total_tokens == 140
    assert result.request_id == "req_safe_id"
    client.responses.parse.assert_called_once_with(
        model="test-model",
        input=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        text_format=SupervisorPlanProposal,
    )


def test_openai_provider_retries_timeout_with_controlled_backoff() -> None:
    timeout = openai.APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    response = SimpleNamespace(output_parsed=proposal(), usage=None, _request_id=None)
    client = MagicMock()
    client.responses.parse.side_effect = [timeout, response]
    sleep = MagicMock()
    provider = OpenAIProvider(
        api_key=None,
        model="test-model",
        timeout_seconds=5,
        max_retries=1,
        sleep=sleep,
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=SupervisorPlanProposal,
    )

    assert result.data.title == "Acquisition plan"
    assert client.responses.parse.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_openai_provider_maps_exhausted_timeout_without_leaking_payload() -> None:
    timeout = openai.APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    client = MagicMock()
    client.responses.parse.side_effect = timeout
    provider = OpenAIProvider(
        api_key=None,
        model="test-model",
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    with pytest.raises(AIProviderTimeoutError, match="timed out"):
        provider.generate_structured(
            system_prompt="sensitive system prompt",
            user_prompt="sensitive command",
            response_model=SupervisorPlanProposal,
        )


def test_openai_provider_retries_missing_structured_output() -> None:
    invalid = SimpleNamespace(output_parsed=None, usage=None, _request_id=None)
    client = MagicMock()
    client.responses.parse.return_value = invalid
    provider = OpenAIProvider(
        api_key=None,
        model="test-model",
        timeout_seconds=5,
        max_retries=1,
        sleep=lambda _: None,
        client=client,
    )

    with pytest.raises(AIInvalidResponseError, match="structured output"):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=SupervisorPlanProposal,
        )

    assert client.responses.parse.call_count == 2


def test_openai_provider_maps_connection_failure() -> None:
    connection_error = openai.APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    client = MagicMock()
    client.responses.parse.side_effect = connection_error
    provider = OpenAIProvider(
        api_key=None,
        model="test-model",
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    with pytest.raises(AIProviderUnavailableError, match="unavailable"):
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=SupervisorPlanProposal,
        )
