from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InferSQL Backend"
    app_version: str = "0.1.0"
    environment: str = "dev"

    # Existing app/runtime settings
    seed_demo_data: bool = True

    # Observability / OTEL
    service_name: str = "infersql-backend"
    console_span_exporter_enabled: bool = False

    # Logging
    log_json: bool = True
    log_level: str = "INFO"

    # LLM configuration
    llm_provider: str = "ollama"  # ollama | gemini | openai | auto
    llm_temperature: float = 0.0

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Gemini
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = "gemini-2.5-flash"

    # OpenAI
    openai_api_key: str | None = Field(default=None)
    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()