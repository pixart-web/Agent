from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

from app.ai.base import LLMResult


class FakeLLMProvider:
    provider_name = "fake"
    model_name = "fake-supervisor-v1"

    def __init__(self, outcomes: Iterable[LLMResult[Any] | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def generate_structured[T: BaseModel](
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> LLMResult[T]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if not self.outcomes:
            raise AssertionError("Fake provider has no configured outcome")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
