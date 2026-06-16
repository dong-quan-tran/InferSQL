from __future__ import annotations

from typing import Protocol

from app.schemas.copilot import CopilotSqlCandidate


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate: ...