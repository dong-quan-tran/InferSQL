from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.catalog.registry import DatasetNotFoundError
from app.core.exceptions import NotFoundError
from app.schemas.catalog import (
    CatalogColumnResponse,
    CatalogDatasetListResponse,
    CatalogDatasetResponse,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _to_dataset_response(summary: dict) -> CatalogDatasetResponse:
    column_descriptions = summary.get("column_descriptions", {})
    column_aliases = summary.get("column_aliases", {})
    column_samples = summary.get("column_samples", {})

    columns = [
        CatalogColumnResponse(
            name=column_name,
            type=summary["types"][column_name],
            description=column_descriptions.get(column_name),
            aliases=column_aliases.get(column_name, []),
            sample_values=[str(value) for value in column_samples.get(column_name, [])],
        )
        for column_name in summary["columns"]
    ]

    return CatalogDatasetResponse(
        name=summary["name"],
        description=summary.get("description"),
        row_count=summary.get("row_count", 0),
        source_path=summary.get("source_path"),
        loaded_at=summary.get("loaded_at"),
        columns=columns,
    )


@router.get("/datasets", response_model=CatalogDatasetListResponse)
def list_datasets(request: Request) -> CatalogDatasetListResponse:
    query_service = request.app.state.query_service

    datasets = [
        _to_dataset_response(
            query_service.dataset_registry.describe_table(
                table_name,
                include_samples=True,
            )
        )
        for table_name in query_service.dataset_registry.list_tables()
    ]

    return CatalogDatasetListResponse(datasets=datasets)


@router.get("/datasets/{dataset_name}", response_model=CatalogDatasetResponse)
def get_dataset(dataset_name: str, request: Request) -> CatalogDatasetResponse:
    query_service = request.app.state.query_service

    try:
        summary = query_service.dataset_registry.describe_table(
            dataset_name,
            include_samples=True,
        )
    except DatasetNotFoundError as exc:
        raise NotFoundError(f"Unknown dataset '{dataset_name}'") from exc

    return _to_dataset_response(summary)