"""Local AI provider: models served by an Ollama runtime on infrastructure Pixart controls.

Kiko never calls an external inference API. This adapter talks HTTP to an Ollama server on
loopback or a private network (enforced by `Settings.ai_local_base_url` validation) and
returns validated Pydantic objects through the same `LLMProvider` protocol the domain uses.

Structured output:
- ``native_schema``: the JSON Schema is sent as Ollama's ``format``; the runtime constrains
  generation to it (works with gemma4 on Ollama 0.40).
- ``prompted``: the schema is placed in the instructions and the answer is parsed leniently
  (code fences removed). For models whose runtime cannot enforce schemas (qwen3.5).

In both modes the answer is validated with the response model. A failed validation is
retried with the validation errors fed back to the model (bounded by ``max_retries``).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Literal, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.base import LLMResult
from app.ai.exceptions import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

T = TypeVar("T", bound=BaseModel)

StructuredMode = Literal["native_schema", "prompted"]
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
MAX_FEEDBACK_CHARS = 1_500


class OllamaProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        structured_mode: StructuredMode = "native_schema",
        think: bool = False,
        keep_alive: str = "30m",
        num_ctx: int = 8192,
        temperature: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.structured_mode = structured_mode
        self.think = think
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.sleep = sleep
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            # trust_env=False: never route local inference through a system HTTP proxy.
            self._client = httpx.Client(timeout=self.timeout_seconds, trust_env=False)
        return self._client

    def _body(self, messages: list[dict[str, str]], schema: dict) -> dict:
        body: dict = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "keep_alive": self.keep_alive,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if self.structured_mode == "native_schema":
            body["format"] = schema
        return body

    def _system(self, system_prompt: str, schema: dict) -> str:
        if self.structured_mode == "native_schema":
            return system_prompt + "\n\nRespond with a single JSON object only."
        return (
            f"{system_prompt}\n\nRespond with a single JSON object only, no prose and no code "
            f"fences, matching this JSON Schema exactly:\n{json.dumps(schema)}"
        )

    @staticmethod
    def _extract_json(content: str) -> str:
        text = _FENCE.sub("", content.strip())
        start, end = text.find("{"), text.rfind("}")
        return text[start : end + 1] if start != -1 and end > start else text

    def _post(self, body: dict) -> dict:
        try:
            response = self._http().post(f"{self.base_url}/api/chat", json=body)
        except httpx.TimeoutException as error:
            raise AIProviderTimeoutError("Local AI model timed out") from error
        except httpx.TransportError as error:
            raise AIProviderUnavailableError("Local AI runtime is not reachable") from error
        if response.status_code == 404:
            raise AIConfigurationError(f"Local AI model '{self.model_name}' is not installed")
        if response.status_code >= 500:
            raise AIProviderUnavailableError("Local AI runtime is unavailable")
        if response.status_code >= 400:
            raise AIConfigurationError("Local AI runtime rejected the request")
        try:
            return response.json()
        except ValueError as error:
            raise AIProviderUnavailableError(
                "Local AI runtime returned an invalid reply"
            ) from error

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> LLMResult[T]:
        schema = response_model.model_json_schema()
        messages = [
            {"role": "system", "content": self._system(system_prompt, schema)},
            {"role": "user", "content": user_prompt},
        ]
        started = time.perf_counter()
        input_tokens = output_tokens = 0
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                reply = self._post(self._body(messages, schema))
                input_tokens += int(reply.get("prompt_eval_count") or 0)
                output_tokens += int(reply.get("eval_count") or 0)
                content = (reply.get("message") or {}).get("content") or ""
                if not content.strip():
                    raise AIInvalidResponseError("Local AI model returned no content")
                try:
                    data = response_model.model_validate_json(self._extract_json(content))
                except ValidationError as error:
                    feedback = str(error)[:MAX_FEEDBACK_CHARS]
                    messages = [
                        *messages,
                        {"role": "assistant", "content": content[:8_000]},
                        {
                            "role": "user",
                            "content": "Your previous answer did not match the required JSON "
                            f"schema:\n{feedback}\nReturn the corrected JSON object only.",
                        },
                    ]
                    raise AIInvalidResponseError(
                        "Local AI model returned an invalid structured answer"
                    ) from error
                return LLMResult(
                    data=data,
                    provider=self.provider_name,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    latency_ms=round((time.perf_counter() - started) * 1000),
                )
            except AIConfigurationError:
                raise
            except (
                AIProviderTimeoutError,
                AIProviderUnavailableError,
                AIInvalidResponseError,
            ) as error:
                last_error = error
            if attempt < self.max_retries:
                self.sleep(0.5 * (2**attempt))
        assert last_error is not None
        raise last_error

    def health(self) -> dict[str, object]:
        """Runtime reachable and model installed? Never raises."""
        try:
            response = self._http().get(f"{self.base_url}/api/tags", timeout=5)
            names = {item.get("name") for item in response.json().get("models", [])}
        except Exception:  # noqa: BLE001 - health must not raise
            return {"reachable": False, "model_installed": False}
        return {"reachable": True, "model_installed": self.model_name in names}
