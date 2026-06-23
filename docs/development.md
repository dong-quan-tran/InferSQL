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

## Migration status

InferSQL has migrated from a custom narrow SQL path to a hybrid architecture centered on Apache DataFusion.[web:65][web:317]

Current state:

- `/query/execute` is DataFusion-backed for production query execution across the supported SQL surface.[web:65][web:321]
- `/query/plan` is hybrid:
  - simple single-table queries may still use the legacy custom planner,
  - broader SQL shapes such as joins, subqueries, and set operations are planned through DataFusion.[web:65][web:317]
- `/query/validate` remains product-owned:
  - it uses SQLGlot plus registry metadata for schema checks and guardrails,
  - it is not the final source of semantic SQL truth.[web:352][web:394]
- The original custom engine remains as a narrow planning/reference layer; it is no longer the primary execution engine.

Practical meaning:

- broad SQL capability should be judged by tested `/query/execute` behavior and broad `/query/plan` behavior,
- not by legacy single-table assumptions from the original planner.

## Current SQL surface (developer view)

InferSQL currently supports a **broad but explicit analytical SQL subset** over registered datasets.[web:65][web:317] DataFusion provides the underlying execution and planning engine; InferSQL exposes the subset that is tested and integrated with product validation.[web:320][web:321]

This file is the ground truth for what is **actually supported and tested**.

### Supported (high-level)

- `SELECT` queries only (no DML/DDL).
- Single-table and multi-table queries over registered datasets.
- Joins:
  - `INNER JOIN`.
  - `LEFT JOIN`.
  - Additional join patterns where tests exist.
- Subqueries:
  - `IN (subquery)`.
  - Subqueries in `FROM` (derived tables).
  - Scalar subqueries in `SELECT`.
  - Scalar subqueries in `WHERE`.
- Set operations:
  - `UNION`.
  - `UNION ALL`.
  - Column-count and type compatibility enforced by the engine.[web:393][web:396]
- Projection:
  - Plain column projection.
  - Projection aliases.
  - Arithmetic and other tested expressions in `SELECT`.
- `WHERE` filters:
  - Column-vs-literal comparisons (e.g., `=`, `!=`, `<`, `<=`, `>`, `>=`).
  - Tested expressions in `WHERE`.
- `ORDER BY`:
  - On projected or queryable columns.
  - On raw expressions where tested.
  - `ASC` and `DESC`.
- `LIMIT` (with offset).
- Aggregates:
  - Basic aggregates such as `COUNT`, `SUM`, `AVG`.
  - Grouped aggregation.
  - `HAVING` over tested grouped queries.
- Basic support for **normalized error behavior**:
  - syntax errors,
  - unknown datasets,
  - unknown columns,
  - ambiguous/unqualified columns across multiple datasets,
  - unsupported or invalid semantics mapped to `UnsupportedQueryError`.

### Validation vs engine responsibilities

Product-level validation (using SQLGlot and registry metadata) is responsible for:

- Enforcing allowed statement types (`SELECT`).
- Ensuring referenced datasets exist in the registry.
- Ensuring referenced columns exist on those datasets.
- Detecting ambiguous unqualified columns across multiple datasets.
- Enforcing a small number of product guardrails, including rejection of `SELECT *` with `GROUP BY` for single-table queries.

DataFusion is responsible for:

- Full semantic correctness of:
  - join semantics,
  - grouped aggregates,
  - `HAVING`,
  - subqueries,
  - set operations,
  - expression legality.[web:393][web:396]
- Query planning and execution correctness.[web:65][web:320][web:321]

The rule of thumb:

- `/query/validate` is a **precheck**:
  - enforces `SELECT`-only,
  - checks datasets and columns against the registry,
  - applies the single-table `SELECT *` with `GROUP BY` guardrail,
  - does not attempt to re-implement engine-level grouped/aggregate/window semantics.
- `/query/execute` and broad `/query/plan` treat DataFusion as the source of truth for SQL semantics and only normalize errors into product types.

### Current `/query/validate` behavior

`POST /query/validate`:

- Accepts a JSON body with `sql` and optional options.
- Returns:

  ```json
  {
    "sql": "...",
    "normalized_sql": "...",
    "is_valid": true,
    "query_type": "SELECT",
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
      "error_origin": null,
      "features": []
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

  - Delegates to DataFusion planning and explain output to obtain logical and physical plans.[web:317][web:320]
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
    "error_origin": null,
    "features": ["join", "set_op"]
  }
  ```

### Current `/query/execute` behavior

`POST /query/execute`:

- Applies the same product-level schema and guardrail validation used by `/query/validate`, then executes via DataFusion.[web:65][web:321]
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
      "error_origin": null,
      "features": ["join", "window"]
    }
  }
  ```

- Logical and physical plans are included only where they are available and meaningful.

### Debug metadata contract

All three endpoints share the same debug metadata shape when `debug=true`:

- `request_id` (string): request correlation ID if available, `"unknown"` otherwise.
- `total_ms` (float): total wall-clock time in milliseconds for the operation.
- `stage` (string): one of `"validate"`, `"plan"`, `"execute"`.
- `engine` (string or null):
  - `null` for `/query/validate`,
  - `"infersql-planner"` for simple `/query/plan` using the custom planner,
  - `"datafusion"` for DataFusion-backed plan/execute paths.
- `error_origin` (string or null):
  - `null` on success,
  - `"engine_execution"` for errors mapped from DataFusion execution or planning failures where available.
- `features` (array of strings):
  - zero or more feature flags inferred from the parsed SQL:
    - `"join"` for queries containing joins,
    - `"set_op"` for queries containing set operations (`UNION`, `INTERSECT`, `EXCEPT`),
    - `"window"` for queries containing window functions,
    - `"derived_from"` for queries with a top-level derived table in `FROM`.

The `features` array is always present in debug output and defaults to an empty list for queries where no feature flags apply.

### Error responses

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
      "error_origin": "engine_execution",
      "features": []
    }
  }
}
```

The mapping is:

- parse or syntax issues → `InvalidQuerySyntaxError` (400).
- unknown table or dataset → `UnknownDatasetError` (typically 404).
- unknown column → `UnknownColumnError` (400).
- unsupported semantics or ambiguous references → `UnsupportedQueryError` (currently treated as a client error where normalized).
- unexpected internal engine failures → 5xx internal error responses.

### What is explicitly not supported (yet)

The following are **not** supported today and should be rejected or documented as such:

- Non-`SELECT` statements:
  - `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, etc.
- Window functions unless and until they are explicitly tested and documented here.
- `ORDER BY` on select-list aliases in the product layer:
  - for example, `SELECT close + 1 AS x FROM prices ORDER BY x` may currently be rejected as an unknown column.
- SQL features that are not yet explicitly tested and documented.
- Advanced engine features like:
  - cost-based optimization,
  - user-defined functions (unless explicitly wired),
  - advanced statistics-based planning.[web:396][web:337]

If you are unsure whether a feature is supported:

- Search for a test in `tests/test_query_execute.py` or `tests/test_query_plan.py`.
- If no test exists, treat the feature as unsupported until one is added.

## Developer guidelines

- **Add tests first** for any new SQL surface you intend to support.
- **Update this file** whenever you expand or restrict the supported SQL subset.
- Keep `/query/validate`, `/query/plan`, and `/query/execute` behavior in sync by reusing validation helpers.
- Keep the documented SQL surface tied to tested behavior, not aspirational claims.
- When in doubt, prefer:
  - precise errors,
  - explicit non-support, and
  - clear documentation over silent behavior changes.