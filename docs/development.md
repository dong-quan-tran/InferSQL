# InferSQL Development

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate  # or source .venv/bin/activate on Unix
pip install -r requirements.txt
```

## Running tests

```bash
python -m pytest
```

All broad-SQL work should land with tests. The full suite includes:

- unit tests for parser, planner, validator, and runner,
- API tests for `/query/validate`, `/query/plan`, `/query/execute`,
- smoke tests for copilot and catalog integration.

## Current SQL surface (developer view)

InferSQL currently supports a **broad but explicit analytical SQL subset** over registered datasets. DataFusion provides the underlying engine [web:26][web:243][web:16]; InferSQL exposes the subset that is tested and integrated with product validation.

This file is the ground truth for what is **actually supported and tested**.

### Supported (high-level)

- `SELECT` queries only (no DML/DDL).
- Single-table and multi-table queries over registered datasets.
- Joins:
  - `INNER JOIN`.
  - Additional join types (e.g., `LEFT JOIN`) where tests exist.
- Subqueries:
  - `IN (subquery)`.
  - Subqueries in `FROM` (derived tables).
  - Some scalar subqueries (as tests are added).
- Set operations:
  - `UNION` / `UNION ALL`.
  - Column-count and type compatibility enforced by the engine.
- Projection:
  - Plain column projection.
  - Projection aliases.
  - Simple expressions in `SELECT` (as validated by tests).
- `WHERE` filters:
  - Column-vs-literal comparisons (e.g., `=`, `!=`, `<`, `<=`, `>`, `>=`).
  - A subset of more complex expressions (where tested).
- `ORDER BY`:
  - On projected or queryable columns.
  - `ASC` and `DESC`.
- `LIMIT` (with offset).
- Aggregates:
  - Basic aggregates such as `COUNT`, `SUM`, `AVG`.
  - Grouped aggregation with product-level guardrails.
- Basic support for **normalized error behavior**:
  - syntax errors,
  - unknown datasets,
  - unknown columns,
  - ambiguous/unqualified columns across multiple datasets,
  - unsupported/invalid semantics (mapped to `UnsupportedQueryError`).

### Validation vs engine responsibilities

Product-level validation (using SQLGlot and registry metadata) is responsible for:

- Enforcing allowed statement types (`SELECT`).
- Ensuring referenced datasets exist in the registry.
- Ensuring referenced columns exist on those datasets.
- Detecting ambiguous unqualified columns across multiple datasets.
- Enforcing a small number of “user-friendly” rules for grouped queries (where still enabled).

DataFusion (the engine) is responsible for:

- Full semantic correctness of:
  - join semantics,
  - grouped aggregates,
  - subqueries,
  - set operations,
  - expression legality.
- Execution performance and correctness.

The rule of thumb:

- `/query/validate` is a **precheck** focusing on schema and product guardrails.
- `/query/execute` and broad `/query/plan` rely on DataFusion for deep SQL semantics.

### Current `/query/validate` behavior

`POST /query/validate`:

- Accepts a JSON body with `sql` and optional options.
- Returns:

  ```json
  {
    "sql": "...",
    "normalized_sql": "...",
    "is_valid": true,
    "query_type": "select",
    "errors": [],
    "tables": ["prices"],
    "columns": ["symbol", "close"],
    "has_where": true,
    "has_group_by": false,
    "has_order_by": true,
    "has_limit": true,
    "debug": {
      "request_id": "...",
      "total_ms": 1.23,
      "stage": "validate",
      "engine": null,
      "error_origin": null
    }
  }
  ```

- `is_valid` reflects product-level validation only. A query can pass validate but still fail execute if engine-level semantics are violated.

### Current `/query/plan` behavior

`POST /query/plan`:

- For simple single-table queries:

  - Uses the legacy custom planner.
  - Returns `engine: "infersql-planner"`.
  - Returns custom `logical_plan` and `physical_plan` nodes.

- For broader SQL (joins, subqueries, unions):

  - Delegates to DataFusion `EXPLAIN` / `EXPLAIN VERBOSE` to obtain logical and physical plans [web:16].
  - Wraps those plans into:

    ```json
    "logical_plan": {
      "node_type": "DataFusionLogicalPlan",
      "details": { "lines": ["..."] },
      "children": []
    },
    "physical_plan": {
      "node_type": "DataFusionPhysicalPlan",
      "details": { "lines": ["..."] },
      "children": []
    }
    ```

  - Sets `engine: "datafusion"`.

- In both cases, `plan` may include a `debug` object:

  ```json
  "debug": {
    "request_id": "...",
    "total_ms": 2.34,
    "stage": "plan",
    "engine": "datafusion",
    "error_origin": null
  }
  ```

### Current `/query/execute` behavior

`POST /query/execute`:

- Validates using the same product-level logic as `/query/validate`, then executes via DataFusion.
- Returns:

  ```json
  {
    "sql": "...",
    "normalized_sql": "...",
    "row_count": 10,
    "columns": ["symbol", "close"],
    "rows": [
      ["AAPL", 189.12],
      ["MSFT", 425.27]
    ],
    "logical_plan": { ... } or null,
    "physical_plan": { ... } or null,
    "debug": {
      "request_id": "...",
      "total_ms": 3.21,
      "stage": "execute",
      "engine": "datafusion",
      "error_origin": null
    }
  }
  ```

- Logical/physical plans are included only where they are available and meaningful.

### Error responses (updated)

Errors are normalized into a structured shape:

```json
{
  "error": {
    "type": "UnknownDatasetError",
    "code": "UNKNOWNDATASETERROR",
    "message": "Unknown dataset 'fundamentals'",
    "status_code": 404,
    "request_id": "...",
    "debug": {
      "stage": "execute",
      "engine": "datafusion",
      "error_origin": "engine_execution"
    }
  }
}
```

The mapping is:

- parse / syntax issues → `InvalidQuerySyntaxError` (400).
- unknown table / dataset → `UnknownDatasetError` (typically 404).
- unknown column → `UnknownColumnError` (400).
- unsupported semantics or ambiguous columns → `UnsupportedQueryError` (400/422 depending on policy).
- unexpected engine failures → a generic “DataFusion execution error” mapped to a 5xx response (when implemented).

### What is explicitly not supported (yet)

The following are **not** supported today and should be rejected or documented as such:

- Non-`SELECT` statements:
  - `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, etc.
- Unbounded, arbitrary window function usage (beyond what is explicitly tested).
- Complex grouped expressions beyond the product-supported rules.
- Advanced engine features like:
  - cost-based optimization,
  - user-defined functions (unless explicitly wired),
  - advanced statistics-based planning.

If you are unsure whether a feature is supported:

- Search for a test in `tests/test_query_execute.py` or `tests/test_query_plan.py`.
- If no test exists, treat the feature as unsupported until one is added.

## Developer guidelines

- **Add tests first** for any new SQL surface you intend to support.
- **Update this file** whenever you expand or restrict the supported SQL subset.
- Keep `/query/validate`, `/query/plan`, and `/query/execute` behavior in sync by reusing validation helpers.
- When in doubt, prefer:
  - precise errors,
  - explicit non-support, and
  - clear documentation over silent behavior changes.