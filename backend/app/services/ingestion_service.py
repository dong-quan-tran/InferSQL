from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from app.core.catalog.registry import DatasetMetadata, DatasetRegistry


class UnsupportedDatasetFormatError(Exception):
    pass


class DatasetAlreadyExistsError(Exception):
    pass

class DatasetLoadError(Exception):
    pass

class DatasetIngestionService:
    def __init__(self, dataset_registry: DatasetRegistry) -> None:
        self.dataset_registry = dataset_registry

    def load_file(
        self,
        name: str,
        path: str,
        description: str | None = None,
        overwrite: bool = False,
    ) -> dict:
        if not overwrite and name in self.dataset_registry.list_tables():
            raise DatasetAlreadyExistsError(f"Dataset '{name}' already exists")

        file_path = Path(path)
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".csv":
                table = pacsv.read_csv(file_path)
            elif suffix == ".parquet":
                table = pq.read_table(file_path)
            else:
                raise UnsupportedDatasetFormatError(
                    f"Unsupported dataset format '{suffix or '<none>'}'"
                )
        except UnsupportedDatasetFormatError:
            raise
        except Exception as exc:
            raise DatasetLoadError(f"Failed to load dataset from '{file_path}'") from exc

        metadata = DatasetMetadata(
            description=description,
            source_path=str(file_path),
            loaded_at=datetime.now(UTC).isoformat(),
        )

        self.dataset_registry.register_table(
            name=name,
            table=table,
            metadata=metadata,
        )

        return self.dataset_registry.describe_table(name)