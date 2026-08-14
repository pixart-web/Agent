from app.ai.base import LLMProvider
from app.ai.exceptions import AIConfigurationError
from app.ai.providers.openai import OpenAIProvider
from app.core.config import get_settings


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )
    raise AIConfigurationError("Fake AI provider must be injected by the application")
