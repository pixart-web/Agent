from app.ai.base import LLMProvider
from app.ai.exceptions import AIConfigurationError
from app.ai.providers.ollama import OllamaProvider
from app.core.config import Settings, get_settings


def build_local_provider(settings: Settings) -> OllamaProvider:
    return OllamaProvider(
        base_url=settings.ai_local_base_url,
        model=settings.ai_local_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_retries=settings.ai_max_retries,
        structured_mode=settings.ai_local_structured_mode,
        think=settings.ai_local_think,
        keep_alive=settings.ai_local_keep_alive,
        num_ctx=settings.ai_local_num_ctx,
    )


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_provider == "ollama":
        return build_local_provider(settings)
    raise AIConfigurationError("Fake AI provider must be injected by the application")
