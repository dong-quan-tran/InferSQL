from __future__ import annotations

import asyncio
import csv
import json
import platform
import socket
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx


OUTPUT_DIR = Path("benchmark_results")
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class BenchmarkResult:
    name: str
    path: str
    iterations: int
    durations_ms: list[float]
    sample_debug: dict[str, Any] | None

    @property
    def min_ms(self) -> float:
        return min(self.durations_ms)

    @property
    def max_ms(self) -> float:
        return max(self.durations_ms)

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.durations_ms)

    @property
    def median_ms(self) -> float:
        return statistics.median(self.durations_ms)

    @property
    def p95_ms(self) -> float:
        sorted_durations = sorted(self.durations_ms)
        index = int(0.95 * (len(sorted_durations) - 1))
        return sorted_durations[index]

    def summary_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "iterations": self.iterations,
            "min_ms": round(self.min_ms, 3),
            "mean_ms": round(self.mean_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "sample_debug": self.sample_debug,
        }


def _safe_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
        value = result.stdout.strip()
        return value or None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def _build_run_metadata(base_url: str, iterations: int, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "timestamp_utc": run_id,
        "base_url": base_url,
        "iterations_per_endpoint": iterations,
        "git_commit_sha": _safe_git("rev-parse", "HEAD"),
        "git_branch": _safe_git("rev-parse", "--abbrev-ref", "HEAD"),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
    }


async def _run_benchmark(
    client: httpx.AsyncClient,
    name: str,
    path: str,
    payload: dict[str, Any],
    iterations: int,
) -> BenchmarkResult:
    durations: list[float] = []
    sample_debug: dict[str, Any] | None = None

    for index in range(iterations):
        start = perf_counter()
        response = await client.post(f"{path}?debug=true", json=payload)
        duration_ms = (perf_counter() - start) * 1000
        durations.append(duration_ms)

        response.raise_for_status()
        data = response.json()

        if index == 0:
            sample_debug = data.get("debug")

    return BenchmarkResult(
        name=name,
        path=path,
        iterations=iterations,
        durations_ms=durations,
        sample_debug=sample_debug,
    )


def _print_result(result: BenchmarkResult) -> None:
    print(f"\n{result.name:=^60}")
    print(f"Iterations: {result.iterations}")
    print(f"Min:        {result.min_ms:.3f} ms")
    print(f"Mean:       {result.mean_ms:.3f} ms")
    print(f"Median:     {result.median_ms:.3f} ms")
    print(f"P95:        {result.p95_ms:.3f} ms")
    print(f"Max:        {result.max_ms:.3f} ms")
    if result.sample_debug:
        print("Sample debug:")
        print(json.dumps(result.sample_debug, indent=2))


def _write_summary_json(
    metadata: dict[str, Any],
    results: list[BenchmarkResult],
) -> Path:
    run_id = metadata["run_id"]
    output_path = OUTPUT_DIR / f"benchmark_summary_{run_id}.json"
    payload = {
        "metadata": metadata,
        "results": [result.summary_dict() for result in results],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def _write_iterations_csv(run_id: str, results: list[BenchmarkResult]) -> Path:
    output_path = OUTPUT_DIR / f"benchmark_iterations_{run_id}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "run_id",
                "endpoint_name",
                "path",
                "iteration",
                "duration_ms",
            ],
        )
        writer.writeheader()

        for result in results:
            for iteration, duration_ms in enumerate(result.durations_ms, start=1):
                writer.writerow(
                    {
                        "run_id": run_id,
                        "endpoint_name": result.name,
                        "path": result.path,
                        "iteration": iteration,
                        "duration_ms": round(duration_ms, 3),
                    }
                )

    return output_path


async def main() -> None:
    base_url = "http://127.0.0.1:8000"
    iterations = 50
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata = _build_run_metadata(base_url=base_url, iterations=iterations, run_id=run_id)

    validate_payload = {"sql": "SELECT symbol, close FROM prices WHERE close > 100"}
    plan_payload = {"sql": "SELECT symbol, close FROM prices ORDER BY close DESC LIMIT 10"}
    execute_payload = {
        "sql": "SELECT symbol, close, volume FROM prices WHERE volume > 900 ORDER BY close DESC"
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        validate_result = await _run_benchmark(
            client=client,
            name="QUERY VALIDATE",
            path="/query/validate",
            payload=validate_payload,
            iterations=iterations,
        )
        plan_result = await _run_benchmark(
            client=client,
            name="QUERY PLAN",
            path="/query/plan",
            payload=plan_payload,
            iterations=iterations,
        )
        execute_result = await _run_benchmark(
            client=client,
            name="QUERY EXECUTE",
            path="/query/execute",
            payload=execute_payload,
            iterations=iterations,
        )

    results = [validate_result, plan_result, execute_result]

    print("Run metadata:")
    print(json.dumps(metadata, indent=2))
    for result in results:
        _print_result(result)

    summary_json_path = _write_summary_json(metadata, results)
    iterations_csv_path = _write_iterations_csv(run_id, results)

    print(f"\nSaved summary JSON to: {summary_json_path}")
    print(f"Saved iterations CSV to: {iterations_csv_path}")


if __name__ == "__main__":
    asyncio.run(main())