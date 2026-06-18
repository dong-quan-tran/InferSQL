from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.base import LLMProvider
from app.services.llm.prompt_builder import build_system_prompt, build_user_prompt


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.0,
    ) -> None:
        self.client = genai.Client(api_key=api_key)
        self._model = model
        self.temperature = temperature

    @property
    def provider_name(self) -> str:
        return "gemini"

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

        response = self.client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )

        text = response.text or ""
        data = json.loads(text)
        return CopilotSqlCandidate.model_validate(data)