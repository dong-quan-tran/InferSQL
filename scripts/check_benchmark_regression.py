from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLDS = {
    "mean_ms": 10.0,
    "p95_ms": 15.0,
}


def _load_summary(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Benchmark summary file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _index_results(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results = summary.get("results", [])
    return {result["name"]: result for result in results}


def _pct_change(baseline: float, candidate: float) -> float:
    if baseline == 0:
        return 0.0
    return ((candidate - baseline) / baseline) * 100.0


def _fmt_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _metadata(summary: dict[str, Any]) -> dict[str, Any]:
    return summary.get("metadata", {})


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python scripts/check_benchmark_regression.py "
            "<baseline_summary.json> <candidate_summary.json> "
            "[mean_threshold_pct] [p95_threshold_pct]"
        )
        raise SystemExit(1)

    baseline_path = sys.argv[1]
    candidate_path = sys.argv[2]

    mean_threshold = (
        float(sys.argv[3]) if len(sys.argv) >= 4 else DEFAULT_THRESHOLDS["mean_ms"]
    )
    p95_threshold = (
        float(sys.argv[4]) if len(sys.argv) >= 5 else DEFAULT_THRESHOLDS["p95_ms"]
    )

    thresholds = {
        "mean_ms": mean_threshold,
        "p95_ms": p95_threshold,
    }

    baseline = _load_summary(baseline_path)
    candidate = _load_summary(candidate_path)

    baseline_results = _index_results(baseline)
    candidate_results = _index_results(candidate)

    baseline_meta = _metadata(baseline)
    candidate_meta = _metadata(candidate)

    print("=" * 90)
    print("BENCHMARK REGRESSION CHECK")
    print("=" * 90)
    print(f"Baseline run:   {baseline_meta.get('run_id', 'unknown')}")
    print(f"Baseline git:   {baseline_meta.get('git_commit_sha', 'unknown')}")
    print(f"Candidate run:  {candidate_meta.get('run_id', 'unknown')}")
    print(f"Candidate git:  {candidate_meta.get('git_commit_sha', 'unknown')}")
    print(f"Thresholds:     mean <= {mean_threshold:.2f}%, p95 <= {p95_threshold:.2f}%")
    print()

    common_endpoints = sorted(set(baseline_results) & set(candidate_results))
    if not common_endpoints:
        print("No common benchmark endpoints found.")
        raise SystemExit(1)

    failures: list[str] = []

    for endpoint_name in common_endpoints:
        print(f"{endpoint_name:=^90}")
        baseline_result = baseline_results[endpoint_name]
        candidate_result = candidate_results[endpoint_name]

        for metric, threshold_pct in thresholds.items():
            baseline_value = float(baseline_result[metric])
            candidate_value = float(candidate_result[metric])
            change_pct = _pct_change(baseline_value, candidate_value)
            status = "PASS"

            if change_pct > threshold_pct:
                status = "FAIL"
                failures.append(
                    f"{endpoint_name} {metric} regressed by {_fmt_pct(change_pct)} "
                    f"(threshold {_fmt_pct(threshold_pct)})"
                )

            print(
                f"{metric:<10} "
                f"baseline={baseline_value:>8.3f} ms   "
                f"candidate={candidate_value:>8.3f} ms   "
                f"change={_fmt_pct(change_pct):>10}   "
                f"status={status}"
            )
        print()

    missing_in_candidate = sorted(set(baseline_results) - set(candidate_results))
    if missing_in_candidate:
        for endpoint_name in missing_in_candidate:
            failures.append(f"Missing endpoint in candidate benchmark: {endpoint_name}")

    if failures:
        print("Regression check failed:\n")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Regression check passed.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()