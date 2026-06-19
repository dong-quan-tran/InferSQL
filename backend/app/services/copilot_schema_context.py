from __future__ import annotations

from app.services.llm.prompt_assets import canonical_aliases_by_column


class CopilotSchemaContextBuilder:
    def __init__(
        self,
        dataset_registry,
        include_samples: bool = True,
        sample_limit: int = 3,
    ) -> None:
        self.dataset_registry = dataset_registry
        self.include_samples = include_samples
        self.sample_limit = sample_limit

    def build(self, table_names: list[str] | None = None) -> str:
        parts: list[str] = []
        selected_tables = table_names or self.dataset_registry.list_tables()
        raw_aliases = canonical_aliases_by_column()

        for table_name in selected_tables:
            description = self.dataset_registry.describe_table(
                table_name,
                include_samples=self.include_samples,
                sample_limit=self.sample_limit,
            )

            lines = [f"Table: {description['name']}"]

            if description.get("description"):
                lines.append(f"Description: {description['description']}")

            lines.append("Columns:")

            column_descriptions = description.get("column_descriptions", {})
            column_samples = description.get("column_samples", {})
            described_aliases = description.get("column_aliases", {})

            if table_name in raw_aliases and isinstance(raw_aliases.get(table_name), dict):
                canonical_aliases = raw_aliases.get(table_name, {})
            else:
                canonical_aliases = raw_aliases

            for column_name in description["columns"]:
                column_type = description["types"][column_name]
                column_description = column_descriptions.get(column_name)

                aliases: list[str] = []
                aliases.extend(canonical_aliases.get(column_name, []))
                aliases.extend(described_aliases.get(column_name, []))

                deduped_aliases: list[str] = []
                seen: set[str] = set()
                for alias in aliases:
                    if alias not in seen:
                        seen.add(alias)
                        deduped_aliases.append(alias)

                samples = column_samples.get(column_name, [])

                line = f"- {column_name}: {column_type}"

                if column_description:
                    line += f" — {column_description}"

                if deduped_aliases:
                    line += f" (aliases: {', '.join(deduped_aliases)})"

                if samples:
                    sample_text = ", ".join(
                        repr(value) if isinstance(value, str) else str(value)
                        for value in samples
                    )
                    line += f" (examples: {sample_text})"

                lines.append(line)

            parts.append("\n".join(lines))

        return "\n\n".join(parts)