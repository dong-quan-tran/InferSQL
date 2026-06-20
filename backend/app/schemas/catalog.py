from __future__ import annotations

from pydantic import BaseModel


class DatasetColumnSummary(BaseModel):
    name: str
    type: str
    description: str | None = None


class DatasetSummary(BaseModel):
    name: str
    description: str | None = None
    row_count: int
    source_path: str | None = None
    loaded_at: str | None = None
    columns: list[DatasetColumnSummary]


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class DatasetDetailResponse(BaseModel):
    name: str
    description: str | None = None
    row_count: int
    source_path: str | None = None
    loaded_at: str | None = None
    columns: list[DatasetColumnSummary]
    column_aliases: dict[str, list[str]]
    column_samples: dict[str, list]


class DatasetIngestRequest(BaseModel):
    name: str
    path: str
    description: str | None = None


class DatasetIngestResponse(BaseModel):
    name: str
    row_count: int
    source_path: str | None = None
    loaded_at: str | None = None
    description: str | None = None