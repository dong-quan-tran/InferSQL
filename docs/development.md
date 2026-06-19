# InferSQL Development

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running tests

```bash
python -m pytest
```

## Supported SQL subset

InferSQL currently supports a small analytical SQL subset focused on single-table `SELECT` queries over Arrow-backed datasets.

### Supported

- `SELECT` queries only.
- Single-table queries.
- Plain column projection, for example:
  - `SELECT symbol FROM prices`
  - `SELECT symbol, close FROM prices`
- Projection aliases, for example:
  - `SELECT close AS price FROM prices`
- `WHERE` filters.
- `ORDER BY` on projected/queryable columns.
- `ASC` and `DESC` sort direction.
- `LIMIT`.
- Basic aggregate functions:
  - `COUNT(*)`
  - `COUNT(column)`
  - `SUM(column)`
  - `AVG(column)`
- `GROUP BY` with MVP validation rules.

### Current ORDER BY behavior

- `ORDER BY` is supported for query planning and execution.
- Ascending and descending ordering are supported.
- Null ordering currently follows the engine’s Arrow-backed sort behavior.
- Current engine contract: `NULL` values sort last.

Example:

```sql
SELECT symbol, close
FROM prices_nulls
ORDER BY close
LIMIT 10
```

### Current GROUP BY / aggregate rules

Grouped aggregation support is intentionally strict in the current MVP.

Rules:

- Every non-aggregated selected column must appear in `GROUP BY`.
- Aggregate expressions are allowed in the select list.
- `SELECT *` with `GROUP BY` is rejected.
- Only plain column expressions are supported in `GROUP BY`.
- Only plain columns and simple aggregates are supported in grouped select lists.

Valid examples:

```sql
SELECT symbol, SUM(close) AS total_close
FROM prices
GROUP BY symbol
```

```sql
SELECT COUNT(*) AS row_count
FROM prices
```

Invalid examples:

```sql
SELECT symbol, close
FROM prices
GROUP BY symbol
```

Reason: `close` is neither aggregated nor listed in `GROUP BY`.

```sql
SELECT *
FROM prices
GROUP BY symbol
```

Reason: `SELECT *` with `GROUP BY` is not supported in the current MVP.

### Unsupported

The following are not supported right now:

- `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, and other non-`SELECT` statements.
- Join queries.
- Multi-table queries.
- Subqueries.
- Window functions.
- HAVING clauses.
- Complex grouped expressions beyond plain columns and basic aggregates.
- Arbitrary expressions in `GROUP BY`.

Example rejected query:

```sql
SELECT prices.symbol, sectors.sector
FROM prices
JOIN sectors ON prices.symbol = sectors.symbol
```

Current behavior:

- Join queries are rejected with an explicit unsupported-feature error.

## API behavior notes

The main query endpoints are:

- `/query/validate`
- `/query/plan`
- `/query/execute`

Validation responses include summary fields such as:

- `query_type`
- `tables`
- `columns`
- `has_where`
- `has_group_by`
- `has_order_by`
- `has_limit`

Error responses are returned in a structured shape:

```json
{
  "error": {
    "type": "UnsupportedQueryError",
    "code": "UNSUPPORTEDQUERYERROR",
    "message": "JOIN queries are not supported right now",
    "status_code": 400,
    "request_id": "..."
  }
}
```