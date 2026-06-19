from __future__ import annotations

from pydantic import BaseModel, Field


class CatalogColumnResponse(BaseModel):
    name: str
    type: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    sample_values: list[str] = Field(default_factory=list)


class CatalogDatasetResponse(BaseModel):
    name: str
    description: str | None = None
    row_count: int
    source_path: str | None = None
    loaded_at: str | None = None
    columns: list[CatalogColumnResponse]


class CatalogDatasetListResponse(BaseModel):
    datasets: list[CatalogDatasetResponse]