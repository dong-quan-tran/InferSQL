from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from app.api.dependencies import get_dataset_registry
from app.core.catalog.registry import DatasetNotFoundError, DatasetRegistry
from app.schemas.catalog import (
    DatasetColumnSummary,
    DatasetDetailResponse,
    DatasetIngestRequest,
    DatasetIngestResponse,
    DatasetListResponse,
    DatasetSummary,
)
from app.services.ingestion_service import (
    DatasetAlreadyExistsError,
    DatasetIngestionService,
    UnsupportedDatasetFormatError,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_ingestion_service(
    registry: DatasetRegistry = Depends(get_dataset_registry),
) -> DatasetIngestionService:
    return DatasetIngestionService(dataset_registry=registry)


def _build_column_summaries(description: dict) -> list[DatasetColumnSummary]:
    column_descriptions = description.get("column_descriptions", {})
    types = description.get("types", {})

    return [
        DatasetColumnSummary(
            name=column_name,
            type=types[column_name],
            description=column_descriptions.get(column_name),
        )
        for column_name in description.get("columns", [])
    ]


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    registry: DatasetRegistry = Depends(get_dataset_registry),
) -> DatasetListResponse:
    datasets = []

    for name in registry.list_tables():
        description = registry.describe_table(name)
        datasets.append(
            DatasetSummary(
                name=description["name"],
                description=description.get("description"),
                row_count=description["row_count"],
                source_path=description.get("source_path"),
                loaded_at=description.get("loaded_at"),
                columns=_build_column_summaries(description),
            )
        )

    return DatasetListResponse(datasets=datasets)


@router.get("/datasets/{name}", response_model=DatasetDetailResponse)
def get_dataset(
    name: str,
    registry: DatasetRegistry = Depends(get_dataset_registry),
):
    try:
        description = registry.describe_table(name, include_samples=True)
    except DatasetNotFoundError as exc:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "type": "NotFoundError",
                    "message": str(exc),
                }
            },
        )

    return DatasetDetailResponse(
        name=description["name"],
        description=description.get("description"),
        row_count=description["row_count"],
        source_path=description.get("source_path"),
        loaded_at=description.get("loaded_at"),
        columns=_build_column_summaries(description),
        column_aliases=description.get("column_aliases", {}),
        column_samples=description.get("column_samples", {}),
    )


@router.post("/ingest", response_model=DatasetIngestResponse)
def ingest_dataset(
    payload: DatasetIngestRequest,
    overwrite: bool = Query(False),
    ingestion_service: DatasetIngestionService = Depends(get_ingestion_service),
):
    try:
        result = ingestion_service.load_file(
            name=payload.name,
            path=payload.path,
            description=payload.description,
            overwrite=overwrite,
        )
    except DatasetAlreadyExistsError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "type": "ConflictError",
                    "message": str(exc),
                }
            },
        )
    except UnsupportedDatasetFormatError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": str(exc),
                }
            },
        )

    return DatasetIngestResponse(
        name=result["name"],
        row_count=result["row_count"],
        source_path=result.get("source_path"),
        loaded_at=result.get("loaded_at"),
        description=result.get("description"),
    )


@router.post("/upload", response_model=DatasetIngestResponse)
def upload_dataset(
    name: str = Form(...),
    description: str | None = Form(None),
    overwrite: bool = Query(False),
    file: UploadFile = File(...),
    ingestion_service: DatasetIngestionService = Depends(get_ingestion_service),
):
    suffix = Path(file.filename or "").suffix.lower()

    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file.file.read())
        temp_path = temp_file.name

    try:
        result = ingestion_service.load_file(
            name=name,
            path=temp_path,
            description=description,
            overwrite=overwrite,
        )
    except DatasetAlreadyExistsError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "type": "ConflictError",
                    "message": str(exc),
                }
            },
        )
    except UnsupportedDatasetFormatError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": str(exc),
                }
            },
        )

    return DatasetIngestResponse(
        name=result["name"],
        row_count=result["row_count"],
        source_path=result.get("source_path"),
        loaded_at=result.get("loaded_at"),
        description=result.get("description"),
    )