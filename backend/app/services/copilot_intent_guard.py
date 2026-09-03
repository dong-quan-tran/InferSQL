from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.catalog.registry import DatasetRegistry
from app.services.llm.prompt_assets import CANONICAL_SYNONYM_RULES


_TOKEN_RE = re.compile(r"[a-z0-9_]+")

AMBIGUOUS_TIME_PHRASES = (
    "latest",
    "newest",
    "most recent",
    "recent",
)

AMBIGUOUS_PERFORMANCE_PHRASES = (
    "best performing",
    "best performer",
    "top performing",
    "top performer",
)

TIME_COLUMN_TOKENS = {
    "date",
    "time",
    "timestamp",
    "datetime",
    "created_at",
    "updated_at",
    "loaded_at",
    "trading_date",
    "trade_date",
    "as_of_date",
}

PERFORMANCE_COLUMN_TOKENS = {
    "return",
    "returns",
    "performance",
    "pct_change",
    "percent_change",
    "change",
    "gain",
    "loss",
    "yield",
}


@dataclass(frozen=True)
class IntentGateDecision:
    allowed: bool
    errors: list[str]
    clarification_question: str | None
    matched_aliases: dict[str, str]
    unsupported_terms: list[str]
    ambiguous_terms: list[str]


def _normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"

    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]

    return token


def _tokenize(text: str) -> set[str]:
    raw_tokens = {token for token in _TOKEN_RE.findall(text.lower()) if token}
    normalized_tokens = {_normalize_token(token) for token in raw_tokens}
    return raw_tokens | normalized_tokens


def _normalize_phrase(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower()))


class CopilotIntentGuard:
    def __init__(self, dataset_registry: DatasetRegistry) -> None:
        self.dataset_registry = dataset_registry

    def evaluate(self, question: str) -> IntentGateDecision:
        normalized_question = _normalize_phrase(question)
        available_terms = self._available_terms()
        aliases = self._approved_aliases()
        matched_aliases = self._matched_aliases(
            normalized_question=normalized_question,
            aliases=aliases,
        )

        ambiguity = self._find_ambiguity(
            normalized_question=normalized_question,
            available_terms=available_terms,
        )
        if ambiguity is not None:
            term, clarification = ambiguity
            return IntentGateDecision(
                allowed=False,
                errors=[clarification],
                clarification_question=clarification,
                matched_aliases=matched_aliases,
                unsupported_terms=[],
                ambiguous_terms=[term],
            )

        unsupported_terms = self._find_unsupported_terms(
            normalized_question=normalized_question,
            available_terms=available_terms,
            aliases=aliases,
        )
        if unsupported_terms:
            joined_terms = ", ".join(f"'{term}'" for term in unsupported_terms)
            error = (
                f"InferSQL cannot answer this request because the available schema "
                f"does not support {joined_terms}. Use a registered dataset, column, "
                f"or approved alias instead."
            )
            return IntentGateDecision(
                allowed=False,
                errors=[error],
                clarification_question=None,
                matched_aliases=matched_aliases,
                unsupported_terms=unsupported_terms,
                ambiguous_terms=[],
            )

        return IntentGateDecision(
            allowed=True,
            errors=[],
            clarification_question=None,
            matched_aliases=matched_aliases,
            unsupported_terms=[],
            ambiguous_terms=[],
        )

    def _available_terms(self) -> set[str]:
        terms: set[str] = set()

        for table_name in self.dataset_registry.list_tables():
            description = self.dataset_registry.describe_table(
                table_name,
                include_samples=False,
            )

            terms |= _tokenize(description["name"])
            terms |= _tokenize(description.get("description") or "")

            column_descriptions = description.get("column_descriptions", {})
            column_aliases = description.get("column_aliases", {})

            for column_name in description["columns"]:
                terms |= _tokenize(column_name)
                terms |= _tokenize(column_descriptions.get(column_name) or "")

                for alias in column_aliases.get(column_name, []):
                    terms |= _tokenize(alias)

        return terms

    def _approved_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}

        for source, target in CANONICAL_SYNONYM_RULES.items():
            normalized_source = _normalize_phrase(source)
            normalized_target = _normalize_phrase(target)

            if normalized_source and normalized_target:
                aliases[normalized_source] = normalized_target

        for table_name in self.dataset_registry.list_tables():
            description = self.dataset_registry.describe_table(
                table_name,
                include_samples=False,
            )

            for column_name, values in description.get("column_aliases", {}).items():
                for value in values:
                    normalized_alias = _normalize_phrase(value)
                    if normalized_alias:
                        aliases[normalized_alias] = column_name

        return aliases

    def _matched_aliases(
        self,
        normalized_question: str,
        aliases: dict[str, str],
    ) -> dict[str, str]:
        return {
            alias: target
            for alias, target in aliases.items()
            if alias in normalized_question
        }

    def _find_ambiguity(
        self,
        normalized_question: str,
        available_terms: set[str],
    ) -> tuple[str, str] | None:
        if self._is_underspecified_join_request(normalized_question):
            return (
                "join",
                (
                    "Clarification needed: the requested datasets can be joined on "
                    "'symbol', but which columns should InferSQL return?"
                ),
            )

        if any(phrase in normalized_question for phrase in AMBIGUOUS_TIME_PHRASES):
            if not self._has_time_column(available_terms):
                return (
                    "latest",
                    (
                        "Clarification needed: this request uses a time-based term such "
                        "as 'latest', but the available datasets do not include a date "
                        "or timestamp column. Which time field should InferSQL use?"
                    ),
                )

        if any(
            phrase in normalized_question for phrase in AMBIGUOUS_PERFORMANCE_PHRASES
        ):
            if not self._has_performance_metric(available_terms):
                return (
                    "best performing",
                    (
                        "Clarification needed: define how performance should be measured "
                        "and over what time period. For example: highest percentage return "
                        "over 30 days."
                    ),
                )

        return None

    def _is_underspecified_join_request(self, normalized_question: str) -> bool:
        if "join" not in normalized_question:
            return False

        if (
            "prices" not in normalized_question
            or "fundamentals" not in normalized_question
        ):
            return False

        requested_output_phrases = (
            "show symbol",
            "show symbols",
            "show close",
            "show price",
            "show prices",
            "show market cap",
            "show market_cap",
            "show row",
            "show rows",
            "show count",
            "show average",
            "show avg",
            "return symbol",
            "return symbols",
            "return close",
            "return price",
            "return prices",
            "return market cap",
            "return market_cap",
            "return row",
            "return rows",
            "return count",
            "return average",
            "return avg",
        )

        return not any(
            phrase in normalized_question for phrase in requested_output_phrases
        )

    def _find_unsupported_terms(
        self,
        normalized_question: str,
        available_terms: set[str],
        aliases: dict[str, str],
    ) -> list[str]:
        unsupported: list[str] = []

        unsupported_concepts = (
            "volume",
            "trade",
            "trades",
            "sector",
        )

        for concept in unsupported_concepts:
            if concept not in normalized_question:
                continue

            if concept in aliases:
                continue

            normalized_concept = _normalize_token(concept)
            if normalized_concept not in available_terms:
                unsupported.append(concept)

        return sorted(set(unsupported))

    def _has_time_column(self, available_terms: set[str]) -> bool:
        return bool(available_terms & TIME_COLUMN_TOKENS)

    def _has_performance_metric(self, available_terms: set[str]) -> bool:
        return bool(available_terms & PERFORMANCE_COLUMN_TOKENS)
