# app/core/engine/executor/filter.py
from __future__ import annotations

from typing import Any

import pyarrow as pa
import pyarrow.compute as pc


class UnsupportedFilterError(ValueError):
    pass


class FilterOperator:
    def execute(
        self,
        table: pa.Table,
        column: str,
        operator: str,
        value: Any,
    ) -> pa.Table:
        field = table[column]

        if operator == "=":
            mask = pc.equal(field, pa.scalar(value))
        elif operator == "!=":
            mask = pc.not_equal(field, pa.scalar(value))
        elif operator == ">":
            mask = pc.greater(field, pa.scalar(value))
        elif operator == ">=":
            mask = pc.greater_equal(field, pa.scalar(value))
        elif operator == "<":
            mask = pc.less(field, pa.scalar(value))
        elif operator == "<=":
            mask = pc.less_equal(field, pa.scalar(value))
        else:
            raise UnsupportedFilterError(f"Unsupported operator: {operator}")

        return table.filter(mask)