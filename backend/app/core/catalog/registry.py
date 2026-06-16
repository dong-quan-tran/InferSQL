from __future__ import annotations

from dataclasses import dataclass, field

import pyarrow as pa
import pyarrow.compute as pc


class DatasetNotFoundError(Exception):
    pass


@dataclass
class DatasetColumnMetadata:
    description: str | None = None


@dataclass
class DatasetMetadata:
    description: str | None = None
    columns: dict[str, DatasetColumnMetadata] = field(default_factory=dict)


@dataclass
class RegisteredDataset:
    table: pa.Table
    metadata: DatasetMetadata = field(default_factory=DatasetMetadata)


class DatasetRegistry:
    def __init__(self) -> None:
        self._datasets: dict[str, RegisteredDataset] = {}

    def register_table(
        self,
        name: str,
        table: pa.Table,
        metadata: DatasetMetadata | None = None,
    ) -> None:
        self._datasets[name] = RegisteredDataset(
            table=table,
            metadata=metadata or DatasetMetadata(),
        )

    def get_table(self, name: str) -> pa.Table:
        try:
            return self._datasets[name].table
        except KeyError as exc:
            raise DatasetNotFoundError(f"Unknown dataset '{name}'") from exc

    def get_schema(self, name: str) -> pa.Schema:
        return self.get_table(name).schema

    def get_metadata(self, name: str) -> DatasetMetadata:
        try:
            return self._datasets[name].metadata
        except KeyError as exc:
            raise DatasetNotFoundError(f"Unknown dataset '{name}'") from exc

    def describe_table(
        self,
        name: str,
        include_samples: bool = False,
        sample_limit: int = 3,
    ) -> dict:
        table = self.get_table(name)
        schema = table.schema
        metadata = self.get_metadata(name)

        column_names = [field.name for field in schema]
        types = {field.name: str(field.type) for field in schema}
        column_descriptions = {
            column_name: column_metadata.description
            for column_name, column_metadata in metadata.columns.items()
            if column_metadata.description
        }

        description = {
            "name": name,
            "description": metadata.description,
            "columns": column_names,
            "types": types,
            "column_descriptions": column_descriptions,
        }

        if include_samples:
            description["sample_values"] = self._sample_values(
                table=table,
                sample_limit=sample_limit,
            )

        return description

    def list_tables(self) -> list[str]:
        return sorted(self._datasets.keys())

    def _sample_values(self, table: pa.Table, sample_limit: int) -> dict[str, list]:
        samples: dict[str, list] = {}

        for column_name in table.column_names:
            column = table[column_name]
            try:
                unique_values = pc.unique(column).to_pylist()
            except Exception:
                samples[column_name] = []
                continue

            clean_values = [value for value in unique_values if value is not None]
            samples[column_name] = clean_values[:sample_limit]

        return samples