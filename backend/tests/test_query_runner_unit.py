import pyarrow as pa

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner


def build_runner() -> tuple[QueryRunner, QueryCompiler]:
    registry = DatasetRegistry()
    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA", "GOOGL"],
                "close": [189.12, 425.27, 1210.54, 176.33],
            }
        ),
    )
    runner = QueryRunner(dataset_registry=registry)
    compiler = QueryCompiler(
        query_parser=QueryParser(),
        physical_planner=PhysicalPlanner(),
    )
    return runner, compiler


def test_query_runner_applies_projection_and_limit() -> None:
    runner, compiler = build_runner()
    compiled = compiler.compile("SELECT symbol FROM prices LIMIT 2")

    result = runner.run(compiled.physical_plan)

    assert result.row_count == 2
    assert result.columns == ["symbol"]
    assert result.rows == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_runner_applies_filter() -> None:
    runner, compiler = build_runner()
    compiled = compiler.compile("SELECT symbol, close FROM prices WHERE close > 400")

    result = runner.run(compiled.physical_plan)

    assert result.row_count == 2
    assert result.columns == ["symbol", "close"]
    assert result.rows == [
        {"symbol": "MSFT", "close": 425.27},
        {"symbol": "NVDA", "close": 1210.54},
    ]


def test_query_runner_applies_offset_and_limit() -> None:
    runner, compiler = build_runner()
    compiled = compiler.compile("SELECT symbol, close FROM prices")

    result = runner.run(compiled.physical_plan, limit=2, offset=1)

    assert result.row_count == 2
    assert result.rows == [
        {"symbol": "MSFT", "close": 425.27},
        {"symbol": "NVDA", "close": 1210.54},
    ]


def test_query_runner_returns_empty_result() -> None:
    runner, compiler = build_runner()
    compiled = compiler.compile("SELECT symbol FROM prices WHERE close > 5000")

    result = runner.run(compiled.physical_plan)

    assert result.row_count == 0
    assert result.columns == ["symbol"]
    assert result.rows == []