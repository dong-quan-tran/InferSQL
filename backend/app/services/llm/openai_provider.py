from __future__ import annotations

import json

from openai import OpenAI

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider
from app.services.llm.prompt_builder import build_system_prompt, build_user_prompt


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.0,
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self._model = model
        self.temperature = temperature

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_sql_candidate(
        self,
        question: str,
        schema_context: str,
    ) -> CopilotSqlCandidate:
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(question=question, schema_context=schema_context)

        response = self.client.chat.completions.create(
            model=self._model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return CopilotSqlCandidate.model_validate(data)