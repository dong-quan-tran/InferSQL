from __future__ import annotations

from typing import Any

import pyarrow as pa
import pyarrow.compute as pc


class AggregateOperator:
    def execute(
        self,
        table: pa.Table,
        group_keys: list[str],
        aggregates: list[dict[str, Any]],
    ) -> pa.Table:
        if not aggregates:
            if not group_keys:
                return table
            return table.select(group_keys).group_by(group_keys).aggregate([])

        if group_keys:
            aggs: list[tuple[str, str]] = []
            aliases: list[str] = []

            for agg in aggregates:
                func = agg["func"]
                column = agg["column"]
                alias = agg["alias"]

                if func == "COUNT" and column == "*":
                    column = table.column_names[0]

                aggs.append((column, func.lower()))
                aliases.append(alias)

            grouped = table.group_by(group_keys).aggregate(aggs)

            renamed_columns: list[str] = []
            aggregate_index = 0
            for name in grouped.column_names:
                if name in group_keys:
                    renamed_columns.append(name)
                else:
                    renamed_columns.append(aliases[aggregate_index])
                    aggregate_index += 1

            return grouped.rename_columns(renamed_columns)

        result_arrays: dict[str, list[Any]] = {}
        for agg in aggregates:
            func = agg["func"]
            column = agg["column"]
            alias = agg["alias"]

            if func == "COUNT":
                if column == "*":
                    value = table.num_rows
                else:
                    value = pc.count(table[column]).as_py()
            elif func == "SUM":
                value = pc.sum(table[column]).as_py()
            elif func == "AVG":
                value = pc.mean(table[column]).as_py()
            else:
                raise ValueError(f"Unsupported aggregate function: {func}")

            result_arrays[alias] = [value]

        return pa.table(result_arrays)