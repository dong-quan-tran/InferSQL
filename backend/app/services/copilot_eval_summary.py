from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CopilotEvalCaseResult:
    id: str
    category: str
    passed: bool
    details: dict[str, Any] | None = None


def build_eval_summary(results: list[CopilotEvalCaseResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    by_category: dict[str, dict[str, Any]] = {}

    for r in results:
        bucket = by_category.setdefault(
            r.category,
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "failed_cases": [],
            },
        )
        bucket["total"] += 1
        if r.passed:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
            bucket["failed_cases"].append(r.id)

    for bucket in by_category.values():
        if bucket["total"] > 0:
            bucket["pass_rate"] = bucket["passed"] / bucket["total"]

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total) if total else 0.0,
        "by_category": by_category,
    }


def assert_eval_thresholds(
    summary: dict[str, Any],
    minimum_overall_pass_rate: float = 0.0,
    minimum_category_pass_rates: dict[str, float] | None = None,
) -> None:
    overall_pass_rate = summary["pass_rate"]
    if overall_pass_rate < minimum_overall_pass_rate:
        raise AssertionError(
            f"Overall pass rate {overall_pass_rate:.2%} is below threshold "
            f"{minimum_overall_pass_rate:.2%}"
        )

    minimum_category_pass_rates = minimum_category_pass_rates or {}
    for category, threshold in minimum_category_pass_rates.items():
        actual = summary["by_category"].get(category, {}).get("pass_rate", 0.0)
        if actual < threshold:
            raise AssertionError(
                f"Category '{category}' pass rate {actual:.2%} is below threshold "
                f"{threshold:.2%}"
            )