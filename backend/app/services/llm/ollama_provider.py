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
            "- Map common business synonyms to actual schema names when supported by the schema context.\n"
            "- Example: if a user says ticker and the schema has symbol, prefer symbol.\n"
        )

        user_prompt = (
            f"Schema context:\n{schema_context}\n\n"
            f"{self._build_few_shot_examples()}\n\n"
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

    def _build_few_shot_examples(self) -> str:
        examples = [
            {
                "question": "Show one stock symbol",
                "response": {
                    "sql": "SELECT symbol FROM prices LIMIT 1",
                    "assumptions": [],
                    "referenced_tables": ["prices"],
                    "referenced_columns": ["symbol"],
                    "confidence": 0.95,
                },
            },
            {
                "question": "Show stock symbols and closing prices",
                "response": {
                    "sql": "SELECT symbol, close FROM prices LIMIT 5",
                    "assumptions": [],
                    "referenced_tables": ["prices"],
                    "referenced_columns": ["symbol", "close"],
                    "confidence": 0.96,
                },
            },
            {
                "question": "Show the closing price for MSFT",
                "response": {
                    "sql": "SELECT symbol, close FROM prices WHERE symbol = 'MSFT'",
                    "assumptions": [],
                    "referenced_tables": ["prices"],
                    "referenced_columns": ["symbol", "close"],
                    "confidence": 0.94,
                },
            },
            {
                "question": "Show stocks with close greater than 200",
                "response": {
                    "sql": "SELECT symbol, close FROM prices WHERE close > 200",
                    "assumptions": [],
                    "referenced_tables": ["prices"],
                    "referenced_columns": ["symbol", "close"],
                    "confidence": 0.93,
                },
            },
            {
                "question": "Show ticker and close",
                "response": {
                    "sql": "SELECT symbol, close FROM prices",
                    "assumptions": ["Mapped ticker to symbol based on schema context."],
                    "referenced_tables": ["prices"],
                    "referenced_columns": ["symbol", "close"],
                    "confidence": 0.84,
                },
            },
        ]

        lines = ["Examples:"]
        for idx, example in enumerate(examples, start=1):
            lines.append(f"Example {idx} question:")
            lines.append(example["question"])
            lines.append("Example output JSON:")
            lines.append(json.dumps(example["response"]))
            lines.append("")

        return "\n".join(lines).strip()