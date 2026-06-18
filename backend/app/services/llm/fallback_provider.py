from __future__ import annotations

import logging

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class FallbackLLMProvider(LLMProvider):
    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    @property
    def provider_name(self) -> str:
        return f"{self.primary.provider_name}+fallback"

    @property
    def model_name(self) -> str:
        return f"{self.primary.model_name}|{self.fallback.model_name}"

    def generate_sql_candidate(
        self,
        question: str,
        schema_context: str,
    ) -> CopilotSqlCandidate:
        try:
            return self.primary.generate_sql_candidate(
                question=question,
                schema_context=schema_context,
            )
        except Exception as exc:
            logger.warning(
                "primary llm provider failed; using fallback",
                extra={
                    "stage": "copilot_generate",
                    "provider": self.primary.provider_name,
                    "fallback_provider": self.fallback.provider_name,
                    "error_type": exc.__class__.__name__,
                },
            )
            return self.fallback.generate_sql_candidate(
                question=question,
                schema_context=schema_context,
            )