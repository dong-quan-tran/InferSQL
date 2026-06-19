from __future__ import annotations

import pyarrow as pa


class ProjectOperator:
    def execute(
        self,
        table: pa.Table,
        columns: list[str],
        projections: list[dict[str, str]] | None = None,
    ) -> pa.Table:
        if not projections:
            return table.select(columns)

        if any(projection["source"] == "*" for projection in projections):
            return table

        source_columns = [projection["source"] for projection in projections]
        output_columns = [projection["output"] for projection in projections]

        projected = table.select(source_columns)

        if source_columns == output_columns:
            return projected

        return projected.rename_columns(output_columns)