from __future__ import annotations

import asyncio
import csv
import json
import platform
import random
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
import pyarrow as pa
from asgi_lifespan import LifespanManager

from app.core.catalog.registry import DatasetColumnMetadata, DatasetMetadata
from app.main import app


OUTPUT_DIR = Path("benchmark_results")
OUTPUT_DIR.mkdir(exist_ok=True)

ROW_SIZES = [1_000, 10_000, 100_000, 1_000_000]
RNG = random.Random(12345)


@dataclass
class Workload:
    name: str
    endpoint: str
    query_shape: str
    dataset_rows: int
    payload: dict[str, Any]


@dataclass
class BenchmarkResult:
    name: str
    endpoint: str
    query_shape: str
    dataset_rows: int
    sql: str
    iterations: int
    durations_ms: list[float]
    sample_debug: dict[str, Any] | None
    sample_row_count: int | None

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
            "endpoint": self.endpoint,
            "query_shape": self.query_shape,
            "dataset_rows": self.dataset_rows,
            "sql": self.sql,
            "iterations": self.iterations,
            "row_count": self.sample_row_count,
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


def _build_run_metadata(iterations: int, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "timestamp_utc": run_id,
        "transport": "httpx.ASGITransport + asgi_lifespan.LifespanManager",
        "iterations_per_workload": iterations,
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


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


def _build_symbols(n: int) -> list[str]:
    return [f"SYM{i:06d}" for i in range(n)]


def _build_close_values(n: int) -> list[float]:
    return [round(RNG.uniform(10.0, 1000.0), 4) for _ in range(n)]


def _build_metric_values(n: int) -> list[float]:
    return [round(RNG.uniform(0.0, 1.0), 6) for _ in range(n)]


def _table_exists(registry, name: str) -> bool:
    try:
        registry.get_table(name)
        return True
    except Exception:
        return False


def seed_benchmark_datasets() -> None:
    registry = app.state.dataset_registry

    for rows in ROW_SIZES:
        prices_name = f"prices_bench_{rows}"
        fundamentals_name = f"fundamentals_bench_{rows}"
        symbols = _build_symbols(rows)

        if not _table_exists(registry, prices_name):
            prices_table = pa.table(
                {
                    "symbol": symbols,
                    "close": _build_close_values(rows),
                }
            )
            registry.register_table(
                prices_name,
                prices_table,
                metadata=DatasetMetadata(
                    description=f"Synthetic prices benchmark dataset with {rows} rows.",
                    columns={
                        "symbol": DatasetColumnMetadata(
                            description="Synthetic stock symbol."
                        ),
                        "close": DatasetColumnMetadata(
                            description="Synthetic closing price."
                        ),
                    },
                ),
            )

        if not _table_exists(registry, fundamentals_name):
            fundamentals_table = pa.table(
                {
                    "symbol": symbols,
                    "metric": _build_metric_values(rows),
                }
            )
            registry.register_table(
                fundamentals_name,
                fundamentals_table,
                metadata=DatasetMetadata(
                    description=f"Synthetic fundamentals benchmark dataset with {rows} rows.",
                    columns={
                        "symbol": DatasetColumnMetadata(
                            description="Synthetic stock symbol."
                        ),
                        "metric": DatasetColumnMetadata(
                            description="Synthetic benchmark metric."
                        ),
                    },
                ),
            )


def build_workloads() -> list[Workload]:
    workloads: list[Workload] = []

    for rows in ROW_SIZES:
        prices = f"prices_bench_{rows}"
        fundamentals = f"fundamentals_bench_{rows}"

        queries = [
            (
                "filter_project_limit",
                f"""
                SELECT symbol, close
                FROM {prices}
                WHERE close > 100
                LIMIT 100
                """,
            ),
            (
                "aggregate_group_by",
                f"""
                SELECT symbol, AVG(close) AS avg_close
                FROM {prices}
                GROUP BY symbol
                """,
            ),
            (
                "order_by_limit",
                f"""
                SELECT symbol, close
                FROM {prices}
                ORDER BY close DESC
                LIMIT 100
                """,
            ),
            (
                "join",
                f"""
                SELECT p.symbol, p.close, f.metric
                FROM {prices} AS p
                JOIN {fundamentals} AS f
                  ON p.symbol = f.symbol
                WHERE p.close > 100
                """,
            ),
        ]

        for shape, sql in queries:
            workloads.append(
                Workload(
                    name=f"EXECUTE {shape.upper()} {rows}",
                    endpoint="/query/execute",
                    query_shape=shape,
                    dataset_rows=rows,
                    payload={"sql": _normalize_sql(sql)},
                )
            )

    return workloads


async def _run_benchmark(
    client: httpx.AsyncClient,
    workload: Workload,
    iterations: int,
    warmup_iterations: int = 3,
) -> BenchmarkResult:
    durations: list[float] = []
    sample_debug: dict[str, Any] | None = None
    sample_row_count: int | None = None

    for _ in range(warmup_iterations):
        response = await client.post(f"{workload.endpoint}?debug=true", json=workload.payload)
        response.raise_for_status()

    for index in range(iterations):
        start = perf_counter()
        response = await client.post(f"{workload.endpoint}?debug=true", json=workload.payload)
        duration_ms = (perf_counter() - start) * 1000
        response.raise_for_status()
        data = response.json()

        durations.append(duration_ms)

        if index == 0:
            sample_debug = data.get("debug")
            sample_row_count = data.get("row_count")

    return BenchmarkResult(
        name=workload.name,
        endpoint=workload.endpoint,
        query_shape=workload.query_shape,
        dataset_rows=workload.dataset_rows,
        sql=workload.payload["sql"],
        iterations=iterations,
        durations_ms=durations,
        sample_debug=sample_debug,
        sample_row_count=sample_row_count,
    )


def _print_result(result: BenchmarkResult) -> None:
    print(f"\n{result.name:=^60}")
    print(f"Endpoint:     {result.endpoint}")
    print(f"Shape:        {result.query_shape}")
    print(f"Rows:         {result.dataset_rows}")
    print(f"Iterations:   {result.iterations}")
    print(f"Row count:    {result.sample_row_count}")
    print(f"Min:          {result.min_ms:.3f} ms")
    print(f"Mean:         {result.mean_ms:.3f} ms")
    print(f"Median:       {result.median_ms:.3f} ms")
    print(f"P95:          {result.p95_ms:.3f} ms")
    print(f"Max:          {result.max_ms:.3f} ms")
    if result.sample_debug:
        print("Sample debug:")
        print(json.dumps(result.sample_debug, indent=2))


def _write_summary_json(metadata: dict[str, Any], results: list[BenchmarkResult]) -> Path:
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
                "name",
                "endpoint",
                "query_shape",
                "dataset_rows",
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
                        "name": result.name,
                        "endpoint": result.endpoint,
                        "query_shape": result.query_shape,
                        "dataset_rows": result.dataset_rows,
                        "iteration": iteration,
                        "duration_ms": round(duration_ms, 3),
                    }
                )

    return output_path


def _write_summary_csv(run_id: str, results: list[BenchmarkResult]) -> Path:
    output_path = OUTPUT_DIR / f"benchmark_summary_{run_id}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "run_id",
                "name",
                "endpoint",
                "query_shape",
                "dataset_rows",
                "sql",
                "iterations",
                "row_count",
                "min_ms",
                "mean_ms",
                "median_ms",
                "p95_ms",
                "max_ms",
            ],
        )
        writer.writeheader()

        for result in results:
            summary = result.summary_dict()
            writer.writerow(
                {
                    "run_id": run_id,
                    "name": summary["name"],
                    "endpoint": summary["endpoint"],
                    "query_shape": summary["query_shape"],
                    "dataset_rows": summary["dataset_rows"],
                    "sql": summary["sql"],
                    "iterations": summary["iterations"],
                    "row_count": summary["row_count"],
                    "min_ms": summary["min_ms"],
                    "mean_ms": summary["mean_ms"],
                    "median_ms": summary["median_ms"],
                    "p95_ms": summary["p95_ms"],
                    "max_ms": summary["max_ms"],
                }
            )

    return output_path


async def main() -> None:
    iterations = 20
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata = _build_run_metadata(iterations=iterations, run_id=run_id)

    async with LifespanManager(app):
        seed_benchmark_datasets()
        workloads = build_workloads()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://bench.local",
            timeout=60.0,
        ) as client:
            results: list[BenchmarkResult] = []
            for workload in workloads:
                print(f"Running benchmark: {workload.name}")
                result = await _run_benchmark(
                    client=client,
                    workload=workload,
                    iterations=iterations,
                )
                results.append(result)

    print("Run metadata:")
    print(json.dumps(metadata, indent=2))
    for result in results:
        _print_result(result)

    summary_json_path = _write_summary_json(metadata, results)
    summary_csv_path = _write_summary_csv(run_id, results)
    iterations_csv_path = _write_iterations_csv(run_id, results)

    print(f"\nSaved summary JSON   to: {summary_json_path}")
    print(f"Saved summary CSV    to: {summary_csv_path}")
    print(f"Saved iterations CSV to: {iterations_csv_path}")


if __name__ == "__main__":
    asyncio.run(main())