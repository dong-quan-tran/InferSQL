from __future__ import annotations

from app.core.catalog.registry import DatasetRegistry


class CopilotSchemaContextBuilder:
    def __init__(
        self,
        dataset_registry: DatasetRegistry,
        include_samples: bool = True,
        sample_limit: int = 3,
    ) -> None:
        self.dataset_registry = dataset_registry
        self.include_samples = include_samples
        self.sample_limit = sample_limit

    def build(self, table_names: list[str] | None = None) -> str:
        parts: list[str] = []
        selected_tables = table_names or self.dataset_registry.list_tables()

        for table_name in selected_tables:
            description = self.dataset_registry.describe_table(
                table_name,
                include_samples=self.include_samples,
                sample_limit=self.sample_limit,
            )

            lines = [f"Table: {table_name}"]

            table_description = description.get("description")
            if table_description:
                lines.append(f"Description: {table_description}")

            lines.append("Columns:")
            for column_name in description["columns"]:
                dtype = description["types"][column_name]
                column_description = description["column_descriptions"].get(column_name)
                sample_values = description.get("sample_values", {}).get(column_name, [])

                column_line = f"- {column_name}: {dtype}"
                if column_description:
                    column_line += f" — {column_description}"
                if sample_values:
                    sample_text = ", ".join(repr(value) for value in sample_values)
                    column_line += f" (examples: {sample_text})"

                lines.append(column_line)

            parts.append("\n".join(lines))

        return "\n\n".join(parts)