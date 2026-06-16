import json
from pathlib import Path

import pyarrow as pa
import pytest

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.schemas.copilot import CopilotSqlCandidate
from app.services.copilot_service import CopilotService


def load_eval_cases() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "copilot_eval_cases.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


EVAL_CASES = load_eval_cases()


class EvalLLMProvider:
    def __init__(self, candidates_by_question: dict[str, list[CopilotSqlCandidate]]) -> None:
        self._candidates_by_question = candidates_by_question
        self._call_counts: dict[str, int] = {}
        self._last_original_question: str | None = None

    @property
    def provider_name(self) -> str:
        return "eval-fake"

    @property
    def model_name(self) -> str:
        return "eval-model"

    def generate_sql_candidate(self, question: str, schema_context: str) -> CopilotSqlCandidate:
        original_question = self._extract_original_question(question)
        self._last_original_question = original_question

        candidates = self._candidates_by_question[original_question]
        index = self._call_counts.get(original_question, 0)
        candidate = candidates[min(index, len(candidates) - 1)]
        self._call_counts[original_question] = index + 1
        return candidate

    def _extract_original_question(self, prompt: str) -> str:
        marker = "Original question:\n"
        if marker in prompt:
            remainder = prompt.split(marker, 1)[1]
            return remainder.split("\n\n", 1)[0].strip()
        return prompt.strip()


class EvalQueryService:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False) -> dict:
        normalized_sql = " ".join(sql.strip().split())
        upper_sql = normalized_sql.upper()

        if " FROM FUNDAMENTALS" in upper_sql or " JOIN FUNDAMENTALS" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown dataset 'fundamentals'"],
                "tables": ["fundamentals"],
                "columns": ["*"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if " FROM TRADES" in upper_sql or " JOIN TRADES" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown dataset 'trades'"],
                "tables": ["trades"],
                "columns": ["volume"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if "TICKER" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown column 'ticker' on dataset 'prices'"],
                "tables": ["prices"],
                "columns": ["ticker", "close"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if "SELECT PRICE " in upper_sql or "SELECT PRICE," in upper_sql or " PRICE FROM " in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown column 'price' on dataset 'prices'"],
                "tables": ["prices"],
                "columns": ["price", "symbol"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if "SECTOR" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unknown column 'sector' on dataset 'prices'"],
                "tables": ["prices"],
                "columns": ["sector"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if "JOIN" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Only single-table queries are supported right now"],
                "tables": ["prices", "fundamentals"],
                "columns": ["*"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        if "COUNT(" in upper_sql or "SUM(" in upper_sql or "AVG(" in upper_sql:
            return {
                "sql": sql,
                "normalized_sql": normalized_sql,
                "is_valid": False,
                "query_type": "SELECT",
                "errors": ["Unsupported SQL expression"],
                "tables": ["prices"],
                "columns": ["*"],
                "has_where": "WHERE" in upper_sql,
                "has_group_by": "GROUP BY" in upper_sql,
                "has_order_by": "ORDER BY" in upper_sql,
                "has_limit": "LIMIT" in upper_sql,
            }

        columns: list[str]
        if "SELECT SYMBOL, CLOSE " in upper_sql or "SELECT SYMBOL, CLOSE FROM " in upper_sql:
            columns = ["symbol", "close"]
        elif "SELECT CLOSE " in upper_sql or "SELECT CLOSE FROM " in upper_sql or "SELECT CLOSE," in upper_sql:
            columns = ["close"]
        elif "SELECT SYMBOL " in upper_sql or "SELECT SYMBOL FROM " in upper_sql or "SELECT SYMBOL," in upper_sql:
            columns = ["symbol"]
        else:
            columns = ["close"]

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": True,
            "query_type": "SELECT",
            "errors": [],
            "tables": ["prices"],
            "columns": columns,
            "has_where": "WHERE" in upper_sql,
            "has_group_by": "GROUP BY" in upper_sql,
            "has_order_by": "ORDER BY" in upper_sql,
            "has_limit": "LIMIT" in upper_sql,
        }

    def execute(self, sql: str, request_id: str | None = None, debug: bool = False) -> dict:
        normalized_sql = " ".join(sql.strip().split())
        self.executed_sql.append(normalized_sql)

        upper_sql = normalized_sql.upper()
        if "SELECT SYMBOL, CLOSE " in upper_sql and "WHERE SYMBOL = 'MSFT'" in upper_sql:
            rows = [{"symbol": "MSFT", "close": 425.27}]
            columns = ["symbol", "close"]
        elif "SELECT CLOSE " in upper_sql and "WHERE SYMBOL = 'AAPL'" in upper_sql:
            rows = [{"close": 189.12}]
            columns = ["close"]
        elif "SELECT SYMBOL, CLOSE " in upper_sql and "WHERE SYMBOL = 'AAPL'" in upper_sql:
            rows = [{"symbol": "AAPL", "close": 189.12}]
            columns = ["symbol", "close"]
        elif "WHERE CLOSE > 200" in upper_sql:
            rows = [
                {"symbol": "MSFT", "close": 425.27},
                {"symbol": "NVDA", "close": 1210.54},
            ]
            columns = ["symbol", "close"]
        elif "WHERE CLOSE > 200" in upper_sql:
            rows = [
                {"symbol": "MSFT", "close": 425.27},
                {"symbol": "NVDA", "close": 1210.54},
            ]
            columns = ["symbol", "close"]
        elif "SYMBOL, CLOSE" in upper_sql or ("SYMBOL" in upper_sql and "CLOSE" in upper_sql):
            rows = [
                {"symbol": "AAPL", "close": 189.12},
                {"symbol": "MSFT", "close": 425.27},
            ]
            columns = ["symbol", "close"]
        else:
            rows = [{"symbol": "AAPL"}]
            columns = ["symbol"]

        return {
            "sql": normalized_sql,
            "normalized_sql": normalized_sql,
            "row_count": len(rows),
            "columns": columns,
            "rows": rows,
            "logical_plan": {"node_type": "Project", "details": {}, "children": []},
            "physical_plan": {"node_type": "Project", "details": {}, "children": []},
        }


def build_registry() -> DatasetRegistry:
    registry = DatasetRegistry()
    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
                "close": [189.12, 425.27, 1210.54, 176.33, 182.41],
            }
        ),
        metadata=DatasetMetadata(
            description="Daily security prices for a small demo universe of stocks.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol such as AAPL, MSFT, NVDA, GOOGL, or AMZN."
                ),
                "close": DatasetColumnMetadata(
                    description="Closing price for the security on the row."
                ),
            },
        ),
    )
    return registry


def build_candidates_by_question() -> dict[str, list[CopilotSqlCandidate]]:
    return {
        "Show one stock symbol": [
            CopilotSqlCandidate(
                sql="SELECT symbol FROM prices LIMIT 1",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol"],
                confidence=0.94,
            )
        ],
        "Show stock symbols and closing prices": [
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices LIMIT 2",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.95,
            )
        ],
        "Show the closing price for MSFT": [
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices WHERE symbol = 'MSFT'",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.93,
            )
        ],
        "Show stocks with close greater than 200": [
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices WHERE close > 200",
                assumptions=[],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.92,
            )
        ],
        "Show ticker and close": [
            CopilotSqlCandidate(
                sql="SELECT ticker, close FROM prices",
                assumptions=["Assumed ticker was a valid column name."],
                referenced_tables=["prices"],
                referenced_columns=["ticker", "close"],
                confidence=0.44,
            ),
            CopilotSqlCandidate(
                sql="SELECT symbol, close FROM prices",
                assumptions=["Mapped ticker to symbol based on schema context."],
                referenced_tables=["prices"],
                referenced_columns=["symbol", "close"],
                confidence=0.82,
            ),
        ],
        "Show stock price for AAPL": [
            CopilotSqlCandidate(
                sql="SELECT price FROM prices WHERE symbol = 'AAPL'",
                assumptions=["Assumed price was a valid column name."],
                referenced_tables=["prices"],
                referenced_columns=["price", "symbol"],
                confidence=0.41,
            ),
            CopilotSqlCandidate(
                sql="SELECT close FROM prices WHERE symbol = 'AAPL'",
                assumptions=["Mapped stock price to close based on schema context."],
                referenced_tables=["prices"],
                referenced_columns=["close", "symbol"],
                confidence=0.79,
            ),
        ],
        "Show volume from trades": [
            CopilotSqlCandidate(
                sql="SELECT volume FROM trades",
                assumptions=["Assumed a trades dataset exists."],
                referenced_tables=["trades"],
                referenced_columns=["volume"],
                confidence=0.22,
            ),
            CopilotSqlCandidate(
                sql="SELECT volume FROM trades",
                assumptions=["Retried but kept the unavailable dataset."],
                referenced_tables=["trades"],
                referenced_columns=["volume"],
                confidence=0.19,
            ),
            CopilotSqlCandidate(
                sql="SELECT volume FROM trades",
                assumptions=["Retried again without resolving the missing dataset."],
                referenced_tables=["trades"],
                referenced_columns=["volume"],
                confidence=0.15,
            ),
        ],
        "Show sector for each stock": [
            CopilotSqlCandidate(
                sql="SELECT sector FROM prices",
                assumptions=["Assumed sector was part of the dataset."],
                referenced_tables=["prices"],
                referenced_columns=["sector"],
                confidence=0.26,
            ),
            CopilotSqlCandidate(
                sql="SELECT sector FROM prices",
                assumptions=["Retried but kept the unavailable column."],
                referenced_tables=["prices"],
                referenced_columns=["sector"],
                confidence=0.21,
            ),
            CopilotSqlCandidate(
                sql="SELECT sector FROM prices",
                assumptions=["Retried again without resolving the missing column."],
                referenced_tables=["prices"],
                referenced_columns=["sector"],
                confidence=0.17,
            ),
        ],
        "Join prices with fundamentals": [
            CopilotSqlCandidate(
                sql="SELECT * FROM fundamentals",
                assumptions=["Assumed a fundamentals dataset exists."],
                referenced_tables=["fundamentals"],
                referenced_columns=["*"],
                confidence=0.21,
            ),
            CopilotSqlCandidate(
                sql="SELECT * FROM fundamentals",
                assumptions=["Retried but kept the unavailable dataset."],
                referenced_tables=["fundamentals"],
                referenced_columns=["*"],
                confidence=0.18,
            ),
            CopilotSqlCandidate(
                sql="SELECT * FROM fundamentals",
                assumptions=["Retried again without resolving the missing dataset."],
                referenced_tables=["fundamentals"],
                referenced_columns=["*"],
                confidence=0.14,
            ),
        ],
        "Join prices with trades and show symbol and volume": [
            CopilotSqlCandidate(
                sql="SELECT prices.symbol, trades.volume FROM prices JOIN trades ON prices.symbol = trades.symbol",
                assumptions=["Assumed join support and a trades dataset exist."],
                referenced_tables=["prices", "trades"],
                referenced_columns=["symbol", "volume"],
                confidence=0.24,
            ),
            CopilotSqlCandidate(
                sql="SELECT prices.symbol, trades.volume FROM prices JOIN trades ON prices.symbol = trades.symbol",
                assumptions=["Retried but kept the unsupported join."],
                referenced_tables=["prices", "trades"],
                referenced_columns=["symbol", "volume"],
                confidence=0.19,
            ),
            CopilotSqlCandidate(
                sql="SELECT prices.symbol, trades.volume FROM prices JOIN trades ON prices.symbol = trades.symbol",
                assumptions=["Retried again without resolving unsupported join behavior."],
                referenced_tables=["prices", "trades"],
                referenced_columns=["symbol", "volume"],
                confidence=0.13,
            ),
        ],
        "Count how many rows are in prices": [
            CopilotSqlCandidate(
                sql="SELECT COUNT(*) FROM prices",
                assumptions=["Assumed aggregation support was available."],
                referenced_tables=["prices"],
                referenced_columns=["*"],
                confidence=0.38,
            ),
            CopilotSqlCandidate(
                sql="SELECT COUNT(*) FROM prices",
                assumptions=["Retried but kept the unsupported aggregate."],
                referenced_tables=["prices"],
                referenced_columns=["*"],
                confidence=0.29,
            ),
            CopilotSqlCandidate(
                sql="SELECT COUNT(*) FROM prices",
                assumptions=["Retried again without resolving aggregate support."],
                referenced_tables=["prices"],
                referenced_columns=["*"],
                confidence=0.22,
            ),
        ],
        "Show the latest stock": [
            CopilotSqlCandidate(
                sql="SELECT symbol FROM prices LIMIT 1",
                assumptions=["Interpreted latest as any single available stock because no time column exists."],
                referenced_tables=["prices"],
                referenced_columns=["symbol"],
                confidence=0.51,
            )
        ],
        "Show the best performing stock": [
            CopilotSqlCandidate(
                sql="SELECT symbol FROM prices",
                assumptions=["Could not determine best performing without a comparison metric or time context."],
                referenced_tables=["prices"],
                referenced_columns=["symbol"],
                confidence=0.28,
            )
        ],
    }


@pytest.mark.parametrize("case", EVAL_CASES, ids=[case["id"] for case in EVAL_CASES])
def test_copilot_eval_cases(case: dict) -> None:
    provider = EvalLLMProvider(build_candidates_by_question())
    query_service = EvalQueryService()
    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=query_service,
        llm_provider=provider,
        max_retries=2,
    )

    result = service.query(case["question"], execute=case["execute"])

    assert result.validation.is_valid is case["expected_valid"]
    assert result.attempts <= case["max_attempts"]

    if "expected_sql_contains" in case:
        normalized_sql = result.validation.normalized_sql
        for fragment in case["expected_sql_contains"]:
            assert fragment in normalized_sql

    if case["expected_valid"]:
        assert result.validation.errors == []
        assert result.validation.columns == case["expected_columns"]

        if "expected_assumptions_contains" in case:
            for expected_assumption in case["expected_assumptions_contains"]:
                assert any(
                    expected_assumption in assumption for assumption in result.candidate.assumptions
                )

        if case["execute"]:
            assert result.execution is not None
            assert result.execution["columns"] == case["expected_columns"]
            assert result.execution["row_count"] == case["expected_row_count"]
        else:
            assert result.execution is None
    else:
        assert result.execution is None
        assert result.validation.errors

        if "expected_error_contains" in case:
            for expected_error in case["expected_error_contains"]:
                assert any(expected_error in error for error in result.validation.errors)

        if "expected_error_any_of" in case:
            assert any(
                any(expected_error in error for error in result.validation.errors)
                for expected_error in case["expected_error_any_of"]
            )