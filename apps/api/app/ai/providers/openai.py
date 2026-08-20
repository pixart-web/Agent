import time
from collections.abc import Callable
from typing import TypeVar

import openai
from openai import OpenAI
from pydantic import BaseModel

from app.ai.base import LLMResult
from app.ai.exceptions import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        sleep: Callable[[float], None] = time.sleep,
        client: OpenAI | None = None,
    ) -> None:
        self._api_key = api_key
        self.model_name = model
        self.max_retries = max_retries
        self.sleep = sleep
        self.client = client
        self.timeout_seconds = timeout_seconds

    def _client(self) -> OpenAI:
        if self.client is not None:
            return self.client
        if not self._api_key:
            raise AIConfigurationError("OpenAI is not configured")
        self.client = OpenAI(
            api_key=self._api_key,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        return self.client

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> LLMResult[T]:
        last_error: Exception | None = None
        started = time.perf_counter()
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client().responses.parse(
                    model=self.model_name,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text_format=response_model,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise AIInvalidResponseError("Provider returned no structured output")
                usage = getattr(response, "usage", None)
                return LLMResult(
                    data=parsed,
                    provider=self.provider_name,
                    model=self.model_name,
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                    total_tokens=getattr(usage, "total_tokens", None),
                    request_id=getattr(response, "_request_id", None),
                    latency_ms=round((time.perf_counter() - started) * 1000),
                )
            except openai.APITimeoutError:
                last_error = AIProviderTimeoutError("AI provider timed out")
            except (openai.APIConnectionError, openai.RateLimitError):
                last_error = AIProviderUnavailableError("AI provider is unavailable")
            except openai.APIStatusError as error:
                if error.status_code < 500:
                    raise AIProviderUnavailableError("AI provider rejected the request") from error
                last_error = AIProviderUnavailableError("AI provider is unavailable")
            except AIInvalidResponseError as error:
                last_error = error

            if attempt < self.max_retries:
                self.sleep(0.25 * (2**attempt))

        if last_error is not None:
            raise last_error
        raise AIProviderUnavailableError("AI provider is unavailable")
