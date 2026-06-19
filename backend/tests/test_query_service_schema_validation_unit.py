import pyarrow as pa
import pytest

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.exceptions import (
    EmptyQueryError,
    UnknownColumnError,
    UnknownDatasetError,
    UnsupportedQueryError,
)
from app.core.settings import get_settings
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner
from app.services.query_service import QueryService


def build_query_service() -> QueryService:
    settings = get_settings().model_copy(update={"seed_demo_data": False})
    registry = DatasetRegistry()
    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "close": [189.12, 425.27],
            }
        ),
    )
    parser = QueryParser()
    compiler = QueryCompiler(
        query_parser=parser,
        physical_planner=PhysicalPlanner(),
    )
    runner = QueryRunner(dataset_registry=registry)
    return QueryService(
        settings=settings,
        dataset_registry=registry,
        query_parser=parser,
        query_compiler=compiler,
        query_runner=runner,
    )


def test_validate_referenced_schema_accepts_known_dataset_and_columns() -> None:
    service = build_query_service()

    service._validate_referenced_schema(
        "SELECT symbol, close FROM prices WHERE close > 100"
    )


def test_validate_referenced_schema_rejects_empty_sql() -> None:
    service = build_query_service()

    with pytest.raises(EmptyQueryError, match="SQL must not be empty"):
        service._validate_referenced_schema("   ")


def test_validate_referenced_schema_rejects_missing_dataset_reference() -> None:
    service = build_query_service()

    with pytest.raises(
        UnsupportedQueryError,
        match="Query must reference a dataset",
    ):
        service._validate_referenced_schema("SELECT 1")


def test_validate_referenced_schema_rejects_multiple_tables() -> None:
    service = build_query_service()

    with pytest.raises(
        UnsupportedQueryError,
        match="JOIN queries are not supported right now",
    ):
        service._validate_referenced_schema(
            "SELECT prices.symbol FROM prices, trades WHERE prices.symbol = trades.symbol"
        )


def test_validate_referenced_schema_rejects_unknown_dataset() -> None:
    service = build_query_service()

    with pytest.raises(UnknownDatasetError, match="Unknown dataset 'missing'"):
        service._validate_referenced_schema("SELECT symbol FROM missing")


def test_validate_referenced_schema_rejects_unknown_column() -> None:
    service = build_query_service()

    with pytest.raises(
        UnknownColumnError,
        match="Unknown column 'volume' on dataset 'prices'",
    ):
        service._validate_referenced_schema("SELECT volume FROM prices")