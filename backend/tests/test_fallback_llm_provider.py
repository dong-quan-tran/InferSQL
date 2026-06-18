from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.fallback_provider import FallbackLLMProvider


class SuccessProvider:
    @property
    def provider_name(self) -> str:
        return "primary"

    @property
    def model_name(self) -> str:
        return "primary-model"

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        return CopilotSqlCandidate(
            sql="SELECT symbol FROM prices LIMIT 1",
            assumptions=[],
            referenced_tables=["prices"],
            referenced_columns=["symbol"],
            confidence=0.91,
        )


class FailingProvider:
    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def model_name(self) -> str:
        return "failing-model"

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        raise RuntimeError("primary failed")


class FallbackProvider:
    @property
    def provider_name(self) -> str:
        return "fallback"

    @property
    def model_name(self) -> str:
        return "fallback-model"

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        return CopilotSqlCandidate(
            sql="SELECT close FROM prices LIMIT 1",
            assumptions=["Used fallback provider"],
            referenced_tables=["prices"],
            referenced_columns=["close"],
            confidence=0.80,
        )


def test_fallback_provider_uses_primary_when_successful() -> None:
    provider = FallbackLLMProvider(
        primary=SuccessProvider(),
        fallback=FallbackProvider(),
    )

    result = provider.generate_sql_candidate(
        question="Show one stock symbol",
        schema_context="Table: prices",
    )

    assert result.sql == "SELECT symbol FROM prices LIMIT 1"


def test_fallback_provider_uses_fallback_on_primary_failure() -> None:
    provider = FallbackLLMProvider(
        primary=FailingProvider(),
        fallback=FallbackProvider(),
    )

    result = provider.generate_sql_candidate(
        question="Show one price",
        schema_context="Table: prices",
    )

    assert result.sql == "SELECT close FROM prices LIMIT 1"
    assert result.assumptions == ["Used fallback provider"]