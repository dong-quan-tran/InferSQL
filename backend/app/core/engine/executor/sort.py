from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc


class SortOperator:
    def execute(self, table: pa.Table, keys: list[dict]) -> pa.Table:
        if not keys:
            return table

        order_map = {
            "ASC": "ascending",
            "DESC": "descending",
        }

        sort_keys = [
            (key["column"], order_map.get(key["direction"], "ascending"))
            for key in keys
        ]

        indices = pc.sort_indices(table, sort_keys=sort_keys)
        return table.take(indices)