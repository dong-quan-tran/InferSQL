from __future__ import annotations

import json

import requests

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider


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

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        schema = CopilotSqlCandidate.model_json_schema()

        system_prompt = (
            "You generate SQL for InferSQL.\n"
            "Rules:\n"
            "- Return JSON only.\n"
            "- Generate only SELECT queries.\n"
            "- Prefer a single-table query.\n"
            "- Only use datasets and columns present in the provided schema context.\n"
            "- Do not invent tables or columns.\n"
            "- Keep SQL compact and executable.\n"
            "- confidence must be between 0 and 1.\n"
        )

        user_prompt = (
            f"Schema context:\n{schema_context}\n\n"
            f"Question:\n{question}\n\n"
            "Return a JSON object matching this schema exactly:\n"
            f"{json.dumps(schema)}"
        )

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
        data = json.loads(content)
        return CopilotSqlCandidate.model_validate(data)