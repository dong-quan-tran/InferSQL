from __future__ import annotations

import asyncio
import random

import pyarrow as pa
from asgi_lifespan import LifespanManager

from app.core.catalog.registry import DatasetColumnMetadata, DatasetMetadata
from app.main import app


ROW_SIZES = [1_000, 10_000, 100_000, 1_000_000]
RNG = random.Random(12345)


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


async def main() -> None:
    async with LifespanManager(app):
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
                print(f"Registered {prices_name}")
            else:
                print(f"Skipped existing {prices_name}")

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
                print(f"Registered {fundamentals_name}")
            else:
                print(f"Skipped existing {fundamentals_name}")


if __name__ == "__main__":
    asyncio.run(main())