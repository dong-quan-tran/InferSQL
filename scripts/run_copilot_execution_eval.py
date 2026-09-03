from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.exceptions import (
    EmptyQueryError,
    InternalServerError,
    InvalidQuerySyntaxError,
    UnknownColumnError,
    UnknownDatasetError,
    UnsupportedQueryError,
)
from app.core.settings import get_settings
from app.services.copilot_service import CopilotService
from app.services.llm.factory import build_llm_provider
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner
from app.services.query_service import QueryService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "copilot_execution_eval_cases.json"
ARTIFACT_DIR = BACKEND_ROOT / "artifacts" / "eval"


@dataclass(frozen=True)
class SafeValidationResult:
    is_valid: bool
    normalized_sql: str
    errors: list[str]
    tables: list[str]
    columns: list[str]
    query_type: str | None
    has_where: bool
    has_group_by: bool
    has_order_by: bool
    has_limit: bool


class SafeQueryService:
    """Converts production parser/validation exceptions into Copilot validation results."""

    def __init__(self, query_service: QueryService) -> None:
        self._query_service = query_service

    def validate(
        self,
        sql: str,
        request_id: str | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        try:
            return self._query_service.validate(
                sql=sql,
                request_id=request_id,
                debug=debug,
            )
        except (
            EmptyQueryError,
            InvalidQuerySyntaxError,
            UnknownColumnError,
            UnknownDatasetError,
            UnsupportedQueryError,
        ) as exc:
            normalized_sql = " ".join(sql.strip().split())
            return asdict(
                SafeValidationResult(
                    is_valid=False,
                    normalized_sql=normalized_sql,
                    errors=[str(exc)],
                    tables=[],
                    columns=[],
                    query_type=None,
                    has_where=False,
                    has_group_by=False,
                    has_order_by=False,
                    has_limit=False,
                )
            )

    def execute(
        self,
        sql: str,
        request_id: str | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        return self._query_service.execute(
            sql=sql,
            request_id=request_id,
            debug=debug,
        )


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

    registry.register_table(
        "fundamentals",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "market_cap": [2900000000000, 3200000000000],
            }
        ),
        metadata=DatasetMetadata(
            description="Basic company fundamentals for a subset of securities.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol shared with the prices dataset."
                ),
                "market_cap": DatasetColumnMetadata(
                    description="Approximate market capitalization in USD."
                ),
            },
        ),
    )

    return registry


def build_query_service(registry: DatasetRegistry) -> QueryService:
    settings = get_settings().model_copy(update={"seed_demo_data": False})
    parser = QueryParser()
    planner = PhysicalPlanner()
    compiler = QueryCompiler(
        query_parser=parser,
        physical_planner=planner,
    )
    runner = QueryRunner(dataset_registry=registry)

    return QueryService(
        settings=settings,
        dataset_registry=registry,
        query_parser=parser,
        query_compiler=compiler,
        query_runner=runner,
    )


def load_cases() -> list[dict[str, Any]]:
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"Missing execution-eval fixture: {FIXTURE_PATH}. "
            "Create it before running this script."
        )

    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def canonicalize_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)

    if isinstance(value, dict):
        return {
            str(key): canonicalize_value(item)
            for key, item in sorted(value.items())
        }

    if isinstance(value, list):
        return [canonicalize_value(item) for item in value]

    return value


def canonicalize_rows(
    rows: list[dict[str, Any]],
    columns: list[str],
    ordered: bool,
    compare_column_names: bool,
) -> list[Any]:
    normalized_rows: list[Any] = []

    for row in rows:
        values = [
            canonicalize_value(row.get(column))
            for column in columns
        ]

        if compare_column_names:
            normalized_rows.append(
                {
                    column: value
                    for column, value in zip(columns, values, strict=True)
                }
            )
        else:
            normalized_rows.append(values)

    if ordered:
        return normalized_rows

    return sorted(
        normalized_rows,
        key=lambda row: json.dumps(row, sort_keys=True, default=str),
    )


def is_aggregate_only(columns: list[str], sql: str) -> bool:
    normalized_sql = " ".join(sql.upper().split())
    aggregate_tokens = ("COUNT(", "AVG(", "SUM(", "MIN(", "MAX(")

    if not any(token in normalized_sql for token in aggregate_tokens):
        return False

    return len(columns) == 1


def execute_reference(
    query_service: QueryService,
    reference_sql: str,
) -> dict[str, Any]:
    return query_service.execute(
        sql=reference_sql,
        request_id="copilot-execution-eval-reference",
        debug=False,
        limit=1000,
    )


def evaluate_case(
    case: dict[str, Any],
    service: CopilotService,
    query_service: QueryService,
) -> dict[str, Any]:
    started = time.perf_counter()
    result = service.query(
        case["question"],
        execute=case.get("execute", True),
        request_id=f"copilot-execution-eval-{case['id']}",
    )
    total_ms = round((time.perf_counter() - started) * 1000.0, 3)

    expected_valid = case["expected_valid"]
    outcome: dict[str, Any] = {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected_valid": expected_valid,
        "actual_valid": result.validation.is_valid,
        "passed": False,
        "failure_reason": None,
        "attempts": result.attempts,
        "repaired": result.repaired,
        "sql": result.candidate.sql,
        "normalized_sql": result.validation.normalized_sql,
        "assumptions": result.candidate.assumptions,
        "validation_errors": result.validation.errors,
        "elapsed_ms": total_ms,
        "reference_sql": case.get("reference_sql"),
        "expected_columns": None,
        "actual_columns": None,
        "expected_rows": None,
        "actual_rows": None,
    }

    if result.validation.is_valid is not expected_valid:
        outcome["failure_reason"] = (
            f"validity mismatch: expected={expected_valid}, "
            f"actual={result.validation.is_valid}"
        )
        return outcome

    if result.attempts > case.get("max_attempts", 3):
        outcome["failure_reason"] = (
            f"attempt limit exceeded: expected <= {case['max_attempts']}, "
            f"actual={result.attempts}"
        )
        return outcome

    if not expected_valid:
        expected_errors = case.get("expected_error_contains", [])
        missing_errors = [
            expected
            for expected in expected_errors
            if not any(
                expected.lower() in actual.lower()
                for actual in result.validation.errors
            )
        ]

        if missing_errors:
            outcome["failure_reason"] = (
                f"missing expected rejection text: {missing_errors!r}; "
                f"actual={result.validation.errors!r}"
            )
            return outcome

        if result.execution is not None:
            outcome["failure_reason"] = "invalid request unexpectedly executed"
            return outcome

        outcome["passed"] = True
        return outcome

    if result.execution is None:
        outcome["failure_reason"] = "valid request did not execute"
        return outcome

    reference_sql = case.get("reference_sql")
    if not reference_sql:
        outcome["failure_reason"] = "valid case is missing reference_sql"
        return outcome

    try:
        expected = execute_reference(query_service, reference_sql)
    except Exception as exc:
        outcome["failure_reason"] = (
            f"reference SQL failed: {exc.__class__.__name__}: {exc}"
        )
        return outcome

    ordered = case.get("ordered", False)
    expected_columns = expected["columns"]
    actual_columns = result.execution["columns"]
    compare_column_names = not (
        case.get("allow_aggregate_alias_variation", False)
        and is_aggregate_only(expected_columns, reference_sql)
        and is_aggregate_only(actual_columns, result.validation.normalized_sql)
    )

    expected_rows = canonicalize_rows(
        expected["rows"],
        expected_columns,
        ordered=ordered,
        compare_column_names=compare_column_names,
    )
    actual_rows = canonicalize_rows(
        result.execution["rows"],
        actual_columns,
        ordered=ordered,
        compare_column_names=compare_column_names,
    )

    outcome["expected_columns"] = expected_columns
    outcome["actual_columns"] = actual_columns
    outcome["expected_rows"] = expected_rows
    outcome["actual_rows"] = actual_rows
    outcome["compared_column_names"] = compare_column_names

    if len(actual_columns) != len(expected_columns):
        outcome["failure_reason"] = (
            f"column-count mismatch: expected={len(expected_columns)}, "
            f"actual={len(actual_columns)}"
        )
        return outcome

    if compare_column_names and actual_columns != expected_columns:
        outcome["failure_reason"] = (
            f"column mismatch: expected={expected_columns!r}, "
            f"actual={actual_columns!r}"
        )
        return outcome

    if actual_rows != expected_rows:
        outcome["failure_reason"] = (
            f"result mismatch: expected={expected_rows!r}, "
            f"actual={actual_rows!r}"
        )
        return outcome

    outcome["passed"] = True
    return outcome


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    valid_cases = [
        result for result in results if result["expected_valid"]
    ]
    invalid_cases = [
        result for result in results if not result["expected_valid"]
    ]

    first_pass_valid = [
        result for result in valid_cases if result["attempts"] == 1
    ]
    repaired_valid = [
        result for result in valid_cases if result["repaired"]
    ]
    repaired_passed = [
        result
        for result in repaired_valid
        if result["passed"]
    ]

    by_category: dict[str, dict[str, Any]] = {}
    for result in results:
        bucket = by_category.setdefault(
            result["category"],
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
            },
        )
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1

    for bucket in by_category.values():
        bucket["pass_rate"] = (
            round(bucket["passed"] / bucket["total"], 4)
            if bucket["total"]
            else 0.0
        )

    elapsed = sorted(result["elapsed_ms"] for result in results)

    def percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = max(0, min(len(values) - 1, round((len(values) - 1) * fraction)))
        return round(values[index], 3)

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "execution_accuracy": round(passed / total, 4) if total else 0.0,
        "valid_case_accuracy": (
            round(
                sum(1 for result in valid_cases if result["passed"])
                / len(valid_cases),
                4,
            )
            if valid_cases
            else 0.0
        ),
        "invalid_request_rejection_accuracy": (
            round(
                sum(1 for result in invalid_cases if result["passed"])
                / len(invalid_cases),
                4,
            )
            if invalid_cases
            else 0.0
        ),
        "first_pass_valid_case_accuracy": (
            round(
                sum(1 for result in first_pass_valid if result["passed"])
                / len(valid_cases),
                4,
            )
            if valid_cases
            else 0.0
        ),
        "repair_success_rate": (
            round(len(repaired_passed) / len(repaired_valid), 4)
            if repaired_valid
            else None
        ),
        "mean_attempts": (
            round(sum(result["attempts"] for result in results) / total, 3)
            if total
            else 0.0
        ),
        "latency_ms": {
            "median": percentile(elapsed, 0.5),
            "p95": percentile(elapsed, 0.95),
            "max": round(max(elapsed), 3) if elapsed else 0.0,
        },
        "by_category": by_category,
    }


def main() -> int:
    registry = build_registry()
    query_service = build_query_service(registry)
    safe_query_service = SafeQueryService(query_service)

    llm_provider = build_llm_provider(
        provider=os.getenv("COPILOT_LLM_PROVIDER", "ollama"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.0")),
        ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180")),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    )

    service = CopilotService(
        dataset_registry=registry,
        query_service=safe_query_service,
        llm_provider=llm_provider,
        max_retries=2,
    )

    results = [
        evaluate_case(
            case=case,
            service=service,
            query_service=query_service,
        )
        for case in load_cases()
    ]
    summary = build_summary(results)

    payload = {
        "metadata": {
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "provider": llm_provider.provider_name,
            "model": llm_provider.model_name,
            "evaluation_type": "production_query_service_execution_equivalence",
            "query_engine": "DataFusion",
            "sql_parser": "SQLGlot",
            "max_retries": 2,
        },
        "summary": summary,
        "results": results,
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = ARTIFACT_DIR / f"copilot_execution_eval_{timestamp}.json"
    artifact_path.write_text(
        json.dumps(payload, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(payload, indent=2, default=str))
    print(f"\nSaved evaluation artifact: {artifact_path}")

    return 0 if summary["failed_cases"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
