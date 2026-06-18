from __future__ import annotations

from app.services.llm.base import LLMProvider
from app.services.llm.fallback_provider import FallbackLLMProvider
from app.services.llm.gemini_provider import GeminiLLMProvider
from app.services.llm.ollama_provider import OllamaLLMProvider
from app.services.llm.openai_provider import OpenAILLMProvider


def build_llm_provider(
    provider: str,
    *,
    ollama_base_url: str,
    ollama_model: str,
    ollama_temperature: float = 0.0,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.5-flash",
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4.1-mini",
) -> LLMProvider:
    ollama = OllamaLLMProvider(
        base_url=ollama_base_url,
        model=ollama_model,
        temperature=ollama_temperature,
    )

    normalized = provider.lower()

    if normalized == "ollama":
        return ollama

    if normalized == "gemini":
        if not gemini_api_key:
            raise ValueError("gemini_api_key is required for provider='gemini'")
        return FallbackLLMProvider(
            primary=GeminiLLMProvider(
                api_key=gemini_api_key,
                model=gemini_model,
            ),
            fallback=ollama,
        )

    if normalized == "openai":
        if not openai_api_key:
            raise ValueError("openai_api_key is required for provider='openai'")
        return FallbackLLMProvider(
            primary=OpenAILLMProvider(
                api_key=openai_api_key,
                model=openai_model,
            ),
            fallback=ollama,
        )

    if normalized == "auto":
        if gemini_api_key:
            return FallbackLLMProvider(
                primary=GeminiLLMProvider(
                    api_key=gemini_api_key,
                    model=gemini_model,
                ),
                fallback=ollama,
            )
        if openai_api_key:
            return FallbackLLMProvider(
                primary=OpenAILLMProvider(
                    api_key=openai_api_key,
                    model=openai_model,
                ),
                fallback=ollama,
            )
        return ollama

    raise ValueError(f"Unsupported llm provider '{provider}'")