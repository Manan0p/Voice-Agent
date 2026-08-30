from apps.agent.llm.base import LLMProvider
from apps.agent.llm.gemini import GeminiProvider
from apps.agent.llm.mock import MockLLMProvider
from packages.shared.config import Settings, get_settings


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Instantiate and return the configured LLM provider."""
    cfg = settings or get_settings()

    if cfg.llm_provider == "gemini":
        return GeminiProvider(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_model,
        )
    elif cfg.llm_provider == "mock":
        return MockLLMProvider()
    else:
        # Default fallback to Gemini
        return GeminiProvider(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_model,
        )
