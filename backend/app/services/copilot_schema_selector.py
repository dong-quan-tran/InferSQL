from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.catalog.registry import DatasetRegistry


_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(text: str) -> set[str]:
    raw_tokens = {token for token in _TOKEN_RE.findall(text.lower()) if token}
    normalized = {_normalize_token(token) for token in raw_tokens}
    return raw_tokens | normalized


@dataclass(frozen=True)
class SchemaSelectionResult:
    table_name: str
    score: int


class CopilotSchemaSelector:
    def __init__(
        self,
        dataset_registry: DatasetRegistry,
        max_tables: int = 3,
    ) -> None:
        self.dataset_registry = dataset_registry
        self.max_tables = max_tables

    def select_tables(self, question: str) -> list[str]:
        question_tokens = _tokenize(question)
        scored_results: list[SchemaSelectionResult] = []

        for table_name in self.dataset_registry.list_tables():
            description = self.dataset_registry.describe_table(
                table_name,
                include_samples=True,
                sample_limit=3,
            )
            score = self._score_table(question_tokens, description)
            scored_results.append(
                SchemaSelectionResult(table_name=table_name, score=score)
            )

        scored_results.sort(key=lambda item: (-item.score, item.table_name))

        positive = [item.table_name for item in scored_results if item.score > 0]
        if positive:
            return positive[: self.max_tables]

        return self.dataset_registry.list_tables()

    def _score_table(self, question_tokens: set[str], description: dict) -> int:
        score = 0

        table_tokens = _tokenize(description["name"])
        score += 6 * len(question_tokens & table_tokens)

        table_description = description.get("description") or ""
        score += 2 * len(question_tokens & _tokenize(table_description))

        for column_name in description["columns"]:
            column_tokens = _tokenize(column_name)
            score += 8 * len(question_tokens & column_tokens)

            column_description = description["column_descriptions"].get(column_name) or ""
            score += 3 * len(question_tokens & _tokenize(column_description))

            for sample_value in description.get("sample_values", {}).get(column_name, []):
                score += 1 * len(question_tokens & _tokenize(str(sample_value)))

        return score