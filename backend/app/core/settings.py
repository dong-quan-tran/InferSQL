from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InferSQL API"
    service_name: str = "infersql-api"
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    seed_demo_data: bool = True
    console_span_exporter_enabled: bool = False
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_temperature: float = 0.0
    remote_llm_model: str = "gpt-4.1-mini"
    remote_llm_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def env(self) -> str:
        return self.environment


@lru_cache
def get_settings() -> Settings:
    return Settings()