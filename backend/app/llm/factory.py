from __future__ import annotations

import structlog

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.cloud_provider import CloudProvider

logger = structlog.get_logger("llm.factory")

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is not None:
        return _provider

    settings = get_settings()

    if settings.llm_provider == "ollama":
        _provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        logger.info("llm_provider_created", provider="ollama", model=settings.ollama_model)
    elif settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI provider")
        _provider = CloudProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url="https://api.openai.com/v1",
            provider_name="openai",
        )
        logger.info("llm_provider_created", provider="openai", model=settings.openai_model)
    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
        _provider = CloudProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            base_url="https://api.anthropic.com/v1",
            provider_name="anthropic",
        )
        logger.info("llm_provider_created", provider="anthropic", model=settings.anthropic_model)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    return _provider


async def close_llm_provider() -> None:
    global _provider
    if _provider is not None:
        await _provider.close()
        _provider = None


def reset_provider() -> None:
    global _provider
    _provider = None
