from __future__ import annotations

import json
import os
from pathlib import Path

import pyarrow as pa

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.services.copilot_eval_summary import (
    CopilotEvalCaseResult,
    assert_eval_thresholds,
    build_eval_summary,
)
from app.services.copilot_service import CopilotService
from app.services.llm.factory import build_llm_provider


def load_eval_cases() -> list[dict]:
    fixture_path = Path("tests") / "fixtures" / "copilot_eval_cases.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


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


class LiveEvalQueryService:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False) -> dict:
        normalized_sql = " ".join(sql.strip().split())
        upper_sql = normalized_sql.upper()

        if not upper_sql.startswith("SELECT"):
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Only SELECT statements are supported"],
                tables=[],
                columns=[],
            )

        if " FROM TRADES" in upper_sql or " JOIN TRADES" in upper_sql:
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Unknown dataset 'trades'"],
                tables=["trades"],
                columns=["volume"],
            )

        if " FROM FUNDAMENTALS" in upper_sql or " JOIN FUNDAMENTALS" in upper_sql:
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Unknown dataset 'fundamentals'"],
                tables=["fundamentals"],
                columns=["*"],
            )

        if "TICKER" in upper_sql:
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Unknown column 'ticker' on dataset 'prices'"],
                tables=["prices"],
                columns=["ticker", "close"],
            )

        if "SELECT PRICE " in upper_sql or "SELECT PRICE," in upper_sql or " PRICE FROM " in upper_sql:
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Unknown column 'price' on dataset 'prices'"],
                tables=["prices"],
                columns=["price", "symbol"],
            )

        if "SECTOR" in upper_sql:
            return self._invalid(
                sql=sql,
                normalized_sql=normalized_sql,
                errors=["Unknown column 'sector' on dataset 'prices'"],
                tables=["prices"],
                columns=["sector"],
            )

        columns = self._infer_columns(upper_sql)

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

    def _infer_columns(self, upper_sql: str) -> list[str]:
        if "COUNT(" in upper_sql:
            return ["count"]
        if "SELECT SYMBOL, CLOSE " in upper_sql or "SELECT SYMBOL, CLOSE FROM " in upper_sql:
            return ["symbol", "close"]
        if "SELECT CLOSE " in upper_sql or "SELECT CLOSE FROM " in upper_sql or "SELECT CLOSE," in upper_sql:
            return ["close"]
        if "SELECT SYMBOL " in upper_sql or "SELECT SYMBOL FROM " in upper_sql or "SELECT SYMBOL," in upper_sql:
            return ["symbol"]
        return ["close"]

    def _invalid(
        self,
        sql: str,
        normalized_sql: str,
        errors: list[str],
        tables: list[str],
        columns: list[str],
    ) -> dict:
        upper_sql = normalized_sql.upper()
        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": False,
            "query_type": "SELECT",
            "errors": errors,
            "tables": tables,
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
        elif "COUNT(" in upper_sql:
            rows = [{"count": 5}]
            columns = ["count"]
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


def assert_eval_case(result, case: dict) -> None:
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
                    expected_assumption in assumption
                    for assumption in result.candidate.assumptions
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


def main() -> None:
    llm_provider = build_llm_provider(
        provider=os.getenv("COPILOT_LLM_PROVIDER", "ollama"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.0")),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    )

    service = CopilotService(
        dataset_registry=build_registry(),
        query_service=LiveEvalQueryService(),
        llm_provider=llm_provider,
        max_retries=2,
    )

    eval_cases = load_eval_cases()
    results: list[CopilotEvalCaseResult] = []
    failures: list[dict] = []

    for case in eval_cases:
        eval_result = service.query(case["question"], execute=case["execute"])

        passed = True
        failure_message = None
        try:
            assert_eval_case(eval_result, case)
        except AssertionError as exc:
            passed = False
            failure_message = str(exc) or "assertion failed"

        results.append(
            CopilotEvalCaseResult(
                id=case["id"],
                category=case.get("category", "uncategorized"),
                passed=passed,
                details=None,
            )
        )

        if not passed:
            failures.append(
                {
                    "id": case["id"],
                    "category": case.get("category", "uncategorized"),
                    "question": case["question"],
                    "sql": eval_result.candidate.sql,
                    "assumptions": eval_result.candidate.assumptions,
                    "validation_errors": eval_result.validation.errors,
                    "normalized_sql": eval_result.validation.normalized_sql,
                    "failure": failure_message,
                }
            )

    summary = build_eval_summary(results)

    print(
        json.dumps(
            {
                "provider": llm_provider.provider_name,
                "model": llm_provider.model_name,
                "summary": summary,
                "failures": failures,
            },
            indent=2,
        )
    )

    assert_eval_thresholds(
        summary,
        minimum_overall_pass_rate=0.5,
        minimum_category_pass_rates={
            "simple_select": 0.5,
            "synonym": 0.5,
            "hallucination": 0.5,
            "unsupported_feature": 0.5,
            "ambiguous": 0.5,
        },
    )


if __name__ == "__main__":
    main()