from __future__ import annotations

import json

import requests

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider
from app.services.llm.prompt_builder import (
    build_sql_candidate_schema,
    build_system_prompt,
    build_user_prompt,
)


class OllamaLLMProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_sql_candidate(
        self,
        question: str,
        schema_context: str,
    ) -> CopilotSqlCandidate:
        schema = build_sql_candidate_schema()
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(question=question, schema_context=schema_context)

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self._model,
                "stream": False,
                "format": schema,
                "options": {"temperature": self.temperature},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        content = payload["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama returned non-JSON content: {content}") from exc

        return CopilotSqlCandidate.model_validate(data)