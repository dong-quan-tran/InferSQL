from __future__ import annotations

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider


class RemoteLLMProvider(LLMProvider):
    def __init__(self, model: str) -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return "remote"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        raise NotImplementedError("Remote LLM provider is not configured yet")