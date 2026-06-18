import pytest

from app.services.llm.factory import build_llm_provider
from app.services.llm.fallback_provider import FallbackLLMProvider
from app.services.llm.ollama_provider import OllamaLLMProvider


def test_factory_builds_ollama_provider() -> None:
    provider = build_llm_provider(
        provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
    )

    assert isinstance(provider, OllamaLLMProvider)
    assert provider.provider_name == "ollama"
    assert provider.model_name == "llama3.1:8b"


def test_factory_builds_gemini_with_fallback() -> None:
    provider = build_llm_provider(
        provider="gemini",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        gemini_api_key="test-key",
        gemini_model="gemini-2.5-flash",
    )

    assert isinstance(provider, FallbackLLMProvider)
    assert provider.provider_name == "gemini+fallback"


def test_factory_builds_openai_with_fallback() -> None:
    provider = build_llm_provider(
        provider="openai",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        openai_api_key="test-key",
        openai_model="gpt-4.1-mini",
    )

    assert isinstance(provider, FallbackLLMProvider)
    assert provider.provider_name == "openai+fallback"


def test_factory_auto_prefers_gemini_when_key_present() -> None:
    provider = build_llm_provider(
        provider="auto",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        gemini_api_key="gemini-key",
        openai_api_key="openai-key",
    )

    assert isinstance(provider, FallbackLLMProvider)
    assert provider.provider_name == "gemini+fallback"


def test_factory_auto_falls_back_to_openai_when_no_gemini_key() -> None:
    provider = build_llm_provider(
        provider="auto",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        openai_api_key="openai-key",
    )

    assert isinstance(provider, FallbackLLMProvider)
    assert provider.provider_name == "openai+fallback"


def test_factory_auto_uses_ollama_when_no_remote_keys() -> None:
    provider = build_llm_provider(
        provider="auto",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
    )

    assert isinstance(provider, OllamaLLMProvider)
    assert provider.provider_name == "ollama"


def test_factory_requires_gemini_key_for_gemini_provider() -> None:
    with pytest.raises(ValueError, match="gemini_api_key is required"):
        build_llm_provider(
            provider="gemini",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
        )


def test_factory_requires_openai_key_for_openai_provider() -> None:
    with pytest.raises(ValueError, match="openai_api_key is required"):
        build_llm_provider(
            provider="openai",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
        )


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported llm provider"):
        build_llm_provider(
            provider="nope",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
        )