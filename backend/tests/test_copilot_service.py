import pyarrow as pa

from app.core.catalog.registry import DatasetRegistry
from app.schemas.copilot import CopilotSqlCandidate
from app.services.copilot_service import CopilotService


class FakeLLMProvider:
    def __init__(self, candidates: list[CopilotSqlCandidate]) -> None:
        self._candidates = candidates
        self._index = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        candidate = self._candidates[min(self._index, len(self._candidates) - 1)]
        self._index += 1
        return candidate


class FakeQueryService:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False) -> dict:
        normalized_sql = " ".join(sql.strip().split())

        if "missing_table" in sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown dataset 'missing_table'"],
                "tables": ["missing_table"],
                "columns": ["symbol"],
                "has_where": False,
                "has_group_by": False,
                "has_order_by": False,
                "has_limit": True,
            }

        if "nope" in sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown column 'nope' on dataset 'prices'"],
                "tables": ["prices"],
                "columns": ["nope"],
                "has_where": False,
                "has_group_by": False,
                "has_order_by": False,
                "has_limit": True,
            }

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": True,
            "query_type": "SELECT",
            "errors": [],
            "tables": ["prices"],
            "columns": ["symbol", "close"],
            "has_where": "WHERE" in sql.upper(),
            "has_group_by": False,
            "has_order_by": False,
            "has_limit": "LIMIT" in sql.upper(),
        }

    def execute(self, sql: str, request_id: str | None = None, debug: bool = False) -> dict:
        self.executed_sql.append(sql)
        return {
            "sql": sql,
            "normalized_sql": " ".join(sql.strip().split()),
            "row_count": 1,
            "columns": ["symbol", "close"],
            "rows": [{"symbol": "MSFT", "close": 425.27}],
            "logical_plan": {"node_type": "Project", "details": {}, "children": []},
            "physical_plan": {"node_type": "Project", "details": {}, "children": []},
        }


def build_registry() -> DatasetRegistry:
    registry = DatasetRegistry()
    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "close": [189.12, 425.27],
            }
        ),
    )
    return registry


def test_copilot_service_returns_valid_candidate_first_try() -> None:
    provider = FakeLLMProvider(
        [
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.92,
            )
        ]
    )
    query_service = FakeQueryService()
    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=query_service,
        llm_provider=provider,
    )

    result = service.query("Show one price row", execute=False)

    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.validation.is_valid is True
    assert result.attempts == 1
    assert result.repaired is False
    assert result.retry_history == []


def test_copilot_service_retries_and_repairs_invalid_candidate() -> None:
    provider = FakeLLMProvider(
        [
            CopilotSqlCandidate(
                sql="SELECT nope FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["nope"],
                confidence=0.40,
            ),
            CopilotSqlCandidate(
                sql="SELECT symbol FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol"],
                confidence=0.81,
            ),
        ]
    )
    query_service = FakeQueryService()
    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=query_service,
        llm_provider=provider,
    )

    result = service.query("Show one symbol", execute=False)

    assert result.validation.is_valid is True
    assert result.candidate.sql == "SELECT symbol FROM prices LIMIT 1"
    assert result.attempts == 2
    assert result.repaired is True
    assert len(result.retry_history) == 1
    assert result.retry_history[0].validation.errors == [
        "Unknown column 'nope' on dataset 'prices'"
    ]


def test_copilot_service_stops_after_max_retries() -> None:
    provider = FakeLLMProvider(
        [
            CopilotSqlCandidate(
                sql="SELECT nope FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["nope"],
                confidence=0.30,
            ),
            CopilotSqlCandidate(
                sql="SELECT nope FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["nope"],
                confidence=0.25,
            ),
            CopilotSqlCandidate(
                sql="SELECT nope FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["nope"],
                confidence=0.20,
            ),
        ]
    )
    query_service = FakeQueryService()
    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=query_service,
        llm_provider=provider,
        max_retries=2,
    )

    result = service.query("Show nope", execute=False)

    assert result.validation.is_valid is False
    assert result.attempts == 3
    assert result.repaired is False
    assert len(result.retry_history) == 2
    assert result.execution is None


def test_copilot_service_executes_only_after_valid_sql() -> None:
    provider = FakeLLMProvider(
        [
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.95,
            )
        ]
    )
    query_service = FakeQueryService()
    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=query_service,
        llm_provider=provider,
    )

    result = service.query("Show one price row", execute=True)

    assert result.validation.is_valid is True
    assert result.execution is not None
    assert query_service.executed_sql == ["SELECT symbol, close FROM prices LIMIT 1"]