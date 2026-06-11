from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    durations_ms: list[float]

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
    def p95_ms(self) -> float:
        sorted_durations = sorted(self.durations_ms)
        index = int(0.95 * (len(sorted_durations) - 1))
        return sorted_durations[index]


async def _run_benchmark(
    client: httpx.AsyncClient,
    name: str,
    path: str,
    payload: dict[str, Any],
    iterations: int,
) -> BenchmarkResult:
    durations: list[float] = []

    for _ in range(iterations):
        start = perf_counter()
        response = await client.post(path, json=payload)
        duration_ms = (perf_counter() - start) * 1000
        durations.append(duration_ms)
        response.raise_for_status()

    return BenchmarkResult(name=name, iterations=iterations, durations_ms=durations)


def _print_result(result: BenchmarkResult) -> None:
    print(f"\n{result.name:=^60}")
    print(f"Iterations: {result.iterations}")
    print(f"Min:        {result.min_ms:.3f} ms")
    print(f"Mean:       {result.mean_ms:.3f} ms")
    print(f"P95:        {result.p95_ms:.3f} ms")
    print(f"Max:        {result.max_ms:.3f} ms")


async def main() -> None:
    base_url = "http://127.0.0.1:8000"
    iterations = 50

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

    _print_result(validate_result)
    _print_result(plan_result)
    _print_result(execute_result)


if __name__ == "__main__":
    asyncio.run(main())