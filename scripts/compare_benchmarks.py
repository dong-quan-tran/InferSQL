from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


METRICS = ["min_ms", "mean_ms", "median_ms", "p95_ms", "max_ms"]


def _load_summary(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Benchmark summary file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _index_results(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results = summary.get("results", [])
    return {result["name"]: result for result in results}


def _format_delta(old_value: float, new_value: float) -> str:
    delta = new_value - old_value
    if old_value == 0:
        percent = 0.0
    else:
        percent = (delta / old_value) * 100

    direction = "faster" if delta < 0 else "slower" if delta > 0 else "no change"
    sign = "+" if delta > 0 else ""

    return f"{sign}{delta:.3f} ms ({sign}{percent:.2f}%) [{direction}]"


def _print_header(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    print("=" * 80)
    print("BENCHMARK COMPARISON")
    print("=" * 80)
    print(f"Baseline run:  {baseline.get('run_id', 'unknown')}")
    print(f"Candidate run: {candidate.get('run_id', 'unknown')}")
    print()


def _print_endpoint_comparison(
    endpoint_name: str,
    baseline_result: dict[str, Any],
    candidate_result: dict[str, Any],
) -> None:
    print(f"{endpoint_name:=^80}")
    for metric in METRICS:
        old_value = float(baseline_result[metric])
        new_value = float(candidate_result[metric])
        delta_text = _format_delta(old_value, new_value)
        print(
            f"{metric:<10} "
            f"baseline={old_value:>8.3f} ms   "
            f"candidate={new_value:>8.3f} ms   "
            f"delta={delta_text}"
        )
    print()


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: python scripts/compare_benchmarks.py "
            "<baseline_summary.json> <candidate_summary.json>"
        )
        raise SystemExit(1)

    baseline_path = sys.argv[1]
    candidate_path = sys.argv[2]

    baseline = _load_summary(baseline_path)
    candidate = _load_summary(candidate_path)

    baseline_results = _index_results(baseline)
    candidate_results = _index_results(candidate)

    _print_header(baseline, candidate)

    common_endpoints = sorted(set(baseline_results) & set(candidate_results))
    if not common_endpoints:
        print("No common benchmark endpoints found between the two files.")
        raise SystemExit(1)

    for endpoint_name in common_endpoints:
        _print_endpoint_comparison(
            endpoint_name,
            baseline_results[endpoint_name],
            candidate_results[endpoint_name],
        )

    missing_in_candidate = sorted(set(baseline_results) - set(candidate_results))
    missing_in_baseline = sorted(set(candidate_results) - set(baseline_results))

    if missing_in_candidate:
        print("Missing in candidate:")
        for name in missing_in_candidate:
            print(f"  - {name}")
        print()

    if missing_in_baseline:
        print("Missing in baseline:")
        for name in missing_in_baseline:
            print(f"  - {name}")
        print()


if __name__ == "__main__":
    main()