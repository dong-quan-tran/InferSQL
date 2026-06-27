# InferSQL Development

InferSQL is a small, test-backed SQL engine and frontend workbench built around a DataFusion-backed analytical subset and a registry-driven catalog.

---

## Local backend setup

```bash
python -m venv .venv
. .venv/Scripts/activate  # or: source .venv/bin/activate on Unix
pip install -r requirements.txt
```

---

## Running backend tests

```bash
python -m pytest
```

All broad-SQL and catalog work should land with tests. The full suite includes:

- unit tests for parser, planner, validator, and runner
- API tests for `/query/validate`, `/query/plan`, `/query/execute`
- API tests for catalog and ingestion endpoints
- smoke tests for copilot and catalog integration

When you broaden the SQL surface, add tests first, update this file, and then wire frontend changes.

---

## Migration status

InferSQL has migrated from a custom narrow SQL path to a hybrid architecture centered on Apache DataFusion.

### Current state

- `/query/execute` is DataFusion-backed for production query execution across the supported SQL surface.
- `/query/plan` is hybrid:
  - simple single-table queries may still use the legacy custom planner,
  - broader SQL shapes such as joins, subqueries, and set operations are planned through DataFusion.
- `/query/validate` remains product-owned:
  - it uses SQLGlot plus registry metadata for schema checks and guardrails,
  - it is not the final source of semantic SQL truth.
- The original custom engine remains as a narrow planning/reference layer; it is no longer the primary execution engine.

### Practical meaning

- Broad SQL capability should be judged by tested `/query/execute` behavior and broad `/query/plan` behavior,
- not by legacy single-table assumptions from the original planner.

---

## Current SQL surface (developer view)

InferSQL currently supports a **broad but explicit analytical SQL subset** over registered datasets. DataFusion provides the underlying execution and planning engine; InferSQL exposes **only** the subset that is tested and integrated with product validation.

A simple mental model:

- **Registry**: defines what datasets/columns exist.
- **Validate**: precheck and guardrails over the registry.
- **Plan**: planning artifacts (hybrid: narrow custom + DataFusion).
- **Execute**: DataFusion-backed engine behavior (source of truth).

This file is the ground truth for what is actually supported and tested. If a feature is not described here and not covered by tests, treat it as unsupported.

---

## Registry and metadata

InferSQL uses the dataset registry as the source of truth for dataset metadata.

The registry owns:

- dataset names
- Arrow-backed column names and column types
- optional dataset descriptions
- optional column descriptions
- source metadata such as `source_path` and `loaded_at`
- optional sample values exposed through catalog detail responses

Other layers derive schema information from the registry rather than maintaining separate schema definitions:

- catalog endpoints serialize registry-backed metadata
- query validation checks datasets and columns against registry schemas
- query execution runs only against datasets that are registered

If a dataset is not present in the registry, it is not queryable.  
If a column is not present in the registry schema for that dataset, it should be treated as unknown.

### Dataset naming conventions

Registered dataset names should follow these conventions:

- lowercase only
- snake_case
- ASCII letters, digits, and underscores only
- stable names once exposed through the API

Recommended examples:

- `prices`
- `prices_nulls`
- `fundamentals`
- `daily_trades`

Avoid:

- spaces (`"stock prices"`)
- hyphens (`"stock-prices"`)
- mixed case (`"Prices"`)
- environment-specific suffixes in public names unless they are part of the intended contract

Column names should also be lowercase snake_case where possible.

---

## Catalog and ingestion

InferSQL exposes a catalog and ingestion API backed by the dataset registry.

### Endpoints

- `/catalog/datasets` lists all registered datasets with:
  - name, description, row count, source path, loaded timestamp
  - column names, types, and optional column descriptions
- `/catalog/datasets/{name}` returns a single dataset detail, including:
  - the same metadata as the list endpoint
  - optional column samples and column aliases
- `/catalog/ingest` ingests a dataset from a local path:
  - supports CSV (`.csv`) via `pyarrow.csv.read_csv`
  - supports Parquet (`.parquet`) via `pyarrow.parquet.read_table`
  - registers the resulting `pa.Table` in the registry with:
    - schema
    - row count
    - `source_path`
    - `loaded_at`
    - optional dataset description
- `/catalog/upload` ingests a dataset from an uploaded file:
  - supports CSV and Parquet uploads
  - writes the upload to a temporary file
  - then reuses the same ingestion path as `/catalog/ingest`

Newly ingested datasets are immediately queryable via `/query/execute` once they are registered in the registry.

### Ingestion rules

- duplicate dataset names:
  - rejected by default with `409 Conflict`
  - allowed when `overwrite=true`, in which case the dataset is replaced
- unsupported file formats:
  - rejected as `400 ValidationError` with `UnsupportedDatasetFormatError`
- missing or unreadable files, malformed CSV, and invalid Parquet:
  - rejected as `400 ValidationError` via a normalized `DatasetLoadError`

On the frontend, these endpoints power a **Catalog Explorer** that:

- shows a dataset list (name, description, row counts) backed by `/catalog/datasets`
- shows a dataset detail view (rows, columns, schema) backed by `/catalog/datasets/{name}`
- exposes quick actions that insert example SQL (e.g. `SELECT * FROM <dataset> LIMIT 10`) into the query workbench editor

---

## Supported SQL (high-level)

Supported today:

- `SELECT` queries only (no DML/DDL).
- Single-table and multi-table queries over registered datasets.
- Joins:
  - `INNER JOIN`
  - `LEFT JOIN`
  - additional join patterns where tests exist
- Subqueries:
  - `IN (subquery)`
  - subqueries in `FROM` (derived tables)
  - scalar subqueries in `SELECT`
  - scalar subqueries in `WHERE`
- Set operations:
  - `UNION`
  - `UNION ALL`
  - column-count and type compatibility enforced by the engine
- Projection:
  - plain column projection
  - projection aliases
  - arithmetic and other tested expressions in `SELECT`
- `WHERE` filters:
  - column-vs-literal comparisons (`=`, `!=`, `<`, `<=`, `>`, `>=`)
  - tested expressions in `WHERE`
- `ORDER BY`:
  - on projected or queryable columns
  - on raw expressions where tested
  - `ASC` and `DESC`
- `LIMIT` (with offset)
- Aggregates:
  - basic aggregates such as `COUNT`, `SUM`, `AVG`
  - grouped aggregation
  - `HAVING` over tested grouped queries
- Normalized error behavior:
  - syntax errors
  - unknown datasets
  - unknown columns
  - ambiguous/unqualified columns across multiple datasets
  - unsupported or invalid semantics mapped to `UnsupportedQueryError`

---

## Validation vs engine responsibilities

Product-level validation (using SQLGlot and registry metadata) is responsible for:

- enforcing allowed statement types (`SELECT`)
- ensuring referenced datasets exist in the registry
- ensuring referenced columns exist on those datasets
- detecting ambiguous unqualified columns across multiple datasets
- enforcing a small number of guardrails, including rejection of `SELECT *` with `GROUP BY` for single-table queries

DataFusion is responsible for:

- full semantic correctness of:
  - join semantics
  - grouped aggregates
  - `HAVING`
  - subqueries
  - set operations
  - expression legality
- query planning and execution correctness

Rule of thumb:

- `/query/validate` is a **precheck**:
  - enforces `SELECT`-only
  - checks datasets and columns against the registry
  - applies the single-table `SELECT *` with `GROUP BY` guardrail
  - does not attempt to re-implement engine-level grouped/aggregate/window semantics
- `/query/execute` and broad `/query/plan` treat DataFusion as the source of truth for SQL semantics and only normalize errors into product types.

---

## Current `/query/validate` behavior

`POST /query/validate`:

- Accepts a JSON body with `sql`.
- Returns a validation envelope, for example:

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

`is_valid` reflects product-level validation only. A query can pass validate but still fail execute if engine-level semantics are violated.

---

## Current `/query/plan` behavior

`POST /query/plan`:

- For simple single-table queries:
  - uses the legacy custom planner
  - returns `engine: "infersql-planner"`
  - returns custom `logical_plan` and `physical_plan` nodes
- For broader SQL (joins, subqueries, unions):
  - delegates to DataFusion planning and explain output to obtain logical and physical plans
  - wraps those plans into:

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

  - sets `engine: "datafusion"`

In both cases, `plan` may include a `debug` object:

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

---

## Current `/query/execute` behavior

`POST /query/execute`:

- Applies the same schema and guardrail validation used by `/query/validate`, then executes via DataFusion.
- Returns, for example:

  ```json
  {
    "sql": "...",
    "normalized_sql": "...",
    "row_count": 10,
    "columns": ["symbol", "close"],
    "rows": [
      { "symbol": "AAPL", "close": 189.12 },
      { "symbol": "MSFT", "close": 425.27 }
    ],
    "logical_plan": { "...": "..." } or null,
    "physical_plan": { "...": "..." } or null,
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

Logical and physical plans are included only where they are available and meaningful.

On the frontend, `/query/execute` responses are surfaced as:

- a JSON view that shows the full response (including plans and debug metadata)
- a tabular view that renders `columns` + `rows` as a result table for the latest execute call

---

## Debug metadata contract

All three endpoints share the same debug metadata shape when `debug=true`:

- `request_id` (string): request correlation ID if available, `"unknown"` otherwise
- `total_ms` (float): total wall-clock time in milliseconds for the operation
- `stage` (string): one of `"validate"`, `"plan"`, `"execute"`
- `engine` (string or null):
  - `null` for `/query/validate`
  - `"infersql-planner"` for simple `/query/plan` using the custom planner
  - `"datafusion"` for DataFusion-backed plan/execute paths
- `error_origin` (string or null):
  - `null` on success
  - `"engine_execution"` for errors mapped from DataFusion execution or planning failures where available
- `features` (array of strings):
  - zero or more feature flags inferred from the parsed SQL:
    - `"join"` for queries containing joins
    - `"set_op"` for queries containing set operations (`UNION`, `INTERSECT`, `EXCEPT`)
    - `"window"` for queries containing window functions
    - `"derived_from"` for queries with a top-level derived table in `FROM`

The `features` array is always present in debug output and defaults to an empty list when no feature flags apply.

---

## Error responses

Errors are normalized into a structured shape, for example:

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

Mapping:

- parse or syntax issues → `InvalidQuerySyntaxError` (400)
- unknown table or dataset → `UnknownDatasetError` (typically 404)
- unknown column → `UnknownColumnError` (400)
- unsupported semantics or ambiguous references → `UnsupportedQueryError` (client error where normalized)
- unexpected internal engine failures → 5xx internal error responses via `InternalServerError`

---

## Explicitly not supported (yet)

The following are **not** supported today and should be rejected or documented as such:

- Non-`SELECT` statements:
  - `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, etc.
- Window functions unless and until they are explicitly tested and documented here.
- `ORDER BY` on select-list aliases in the product layer:
  - e.g. `SELECT close + 1 AS x FROM prices ORDER BY x` may currently be rejected as an unknown column.
- SQL features that are not yet explicitly tested and documented.
- Advanced engine features like:
  - cost-based optimization
  - user-defined functions (unless explicitly wired)
  - advanced statistics-based planning

If unsure whether a feature is supported:

- search for a test in `tests/test_query_execute.py` or `tests/test_query_plan.py`
- if no test exists, treat the feature as unsupported until one is added.

---

## Developer guidelines

- Add tests first for any new SQL surface you intend to support.
- Update this file whenever you expand or restrict the supported SQL subset or change catalog/ingestion behavior.
- Keep `/query/validate`, `/query/plan`, and `/query/execute` behavior in sync by reusing validation helpers.
- Tie the documented SQL surface to tested behavior, not aspirational claims.
- Prefer:
  - precise errors
  - explicit non-support
  - clear documentation over silent behavior changes.

---

## Copilot and eval harness

InferSQL includes a small, self-contained copilot layer that generates SQL candidates from natural language questions over registered datasets. The copilot flow is test-backed and designed to support multiple LLM providers.

### Copilot architecture

- `CopilotService` owns the high-level query flow:
  - builds schema context from the dataset registry
  - calls an `LLMProvider` to generate a `CopilotSqlCandidate`
  - validates the candidate via the query service (same behavior as `/query/validate`)
  - optionally executes the candidate via the query service (same behavior as `/query/execute`)
  - returns a structured result with validation, execution (optional), and candidate metadata
- `LLMProvider` is the common interface for all LLM backends, with concrete implementations such as:
  - a local provider (e.g. Ollama) with no paid dependencies
  - optional remote providers (e.g. Gemini, OpenAI) with lazy imports and optional SDKs
- A provider factory centralizes selection:
  - reads a provider name (e.g. `ollama`, `gemini`, `openai`, `auto`)
  - constructs the appropriate provider with configuration (base URL, model, temperature)
  - can wrap providers in a fallback wrapper to ensure a baseline provider is always available

This abstraction means you can add or switch LLM backends without changing `CopilotService` or the rest of the API layer; only factory configuration and dependencies need to change.

### Copilot prompts

Copilot uses a prompt builder explicitly aligned with the tested broad SQL surface and structured-output requirements:

- System prompt:
  - generate only `SELECT` queries over registered datasets
  - use the tested analytical subset (joins, grouped aggregates, `HAVING`, subqueries, set ops)
  - ground all references in the provided schema (no invented tables/columns)
  - qualify columns in multi-table queries
  - map business synonyms (e.g. “ticker”, “price”) to canonical schema columns and record mappings in `assumptions`
  - choose conservative interpretations for ambiguous questions and document limitations
  - return exactly one JSON object matching the `CopilotSqlCandidate` schema
- User prompt:
  - injects registry-backed schema context, synonym guidance, and few-shot examples
  - encourages:
    - minimal valid queries that answer the question
    - joins only when necessary, with explicit, schema-backed join conditions
    - grouped aggregates and `HAVING` when appropriate
    - subqueries (`IN`, scalar, derived tables) where needed
    - explicit `assumptions` for repairs rather than silent changes

---

## Copilot evals

Copilot behavior is covered by an eval harness and two entry points:

- Unit-level evals:
  - use a deterministic eval provider that returns fake `CopilotSqlCandidate` objects
  - use a fake query service that:
    - normalizes SQL and inspects for known patterns
    - simulates product behavior for valid single-table queries, joins, aggregates
    - simulates errors for unknown datasets/columns and unsupported semantics
  - load eval cases from a JSON fixture (`id`, `category`, `question`, `execute`, expectations)
  - assert each case individually and build per-category metrics with minimum pass rate thresholds
- Live eval script:
  - runs `CopilotService` against a real provider (typically the local provider)
  - uses Arrow-backed datasets registered through the real registry
  - reuses the same eval cases and assertion logic
  - prints a JSON summary with provider, model, overall pass rate, per-category pass rates, and failing-case details
  - enforces thresholds so you can fail a CI job or local check when regressions occur

Workflow for broadening Copilot’s reliable surface:

1. Add new eval cases (and extend the eval query service where needed).
2. Tune prompts or provider configuration until the eval suite and live eval both pass.
3. Update this file and any roadmap notes to document the new supported behavior.

### Running copilot evals

To run just the copilot eval tests:

```bash
python -m pytest tests/test_copilot_eval.py
```

To run the live copilot eval script (local provider example):

```bash
COPILOT_LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1 \
python scripts/run_copilot_live_eval.py
```

---

## Performance benchmarks (Phase 12)

Phase 12 adds a small, repeatable performance harness that exercises `/query/execute` against synthetic Arrow tables registered in the in-memory dataset registry.

- Benchmark script: `scripts/benchmark_queries.py`.
- It seeds synthetic benchmark datasets into the live registry (in-memory only), for multiple row sizes (e.g. 1k, 10k, 100k, 1M).
- Tables include simple numeric and joinable shapes (e.g. `prices_bench_*`, `fundamentals_bench_*`).

The script runs query shapes such as:

- `filter_project_limit`
- `aggregate_group_by`
- `order_by_limit`
- `join`

Each workload is executed multiple times against the ASGI app in-process, using the seeded registry instance.

### Running the benchmark

```bash
python scripts/benchmark_queries.py
```

The script:

- wraps the FastAPI app so startup/shutdown hooks run and populate `app.state`
- seeds synthetic benchmark datasets into the in-memory registry
- runs all workloads against `/query/execute?debug=true`
- records per-iteration latency and summary statistics
- writes results into `benchmark_results/`

Artifacts typically include:

- `benchmark_results/benchmark_summary_<RUN_ID>.json`:
  - run metadata (Python version, platform, commit)
  - one summary per workload (query shape, row count, SQL, min/mean/median/p95/max latency, sample row count)
- `benchmark_results/benchmark_summary_<RUN_ID>.csv`:
  - tabular summary suitable for spreadsheets
- `benchmark_results/benchmark_iterations_<RUN_ID>.csv`:
  - per-iteration latency records for detailed analysis

To establish or update a baseline, copy a specific run’s summary files to stable names, e.g.:

```bash
cp benchmark_results/benchmark_summary_<RUN_ID>.json benchmark_results/benchmark_summary_phase12_baseline.json
cp benchmark_results/benchmark_summary_<RUN_ID>.csv  benchmark_results/benchmark_summary_phase12_baseline.csv
```

Future performance work should:

- keep using this script as the canonical latency harness for `/query/execute`
- extend it with additional workloads only when they are representative and stable
- document any new workloads or dataset shapes here

---

## Frontend (Phase F1–F9 overview)

The InferSQL frontend is a Vite + React + TypeScript app that exposes the engine and catalog via a workbench UI.

High-level:

- Tech stack:
  - Vite + React + TypeScript
  - Tailwind for styling
  - TanStack Query for data fetching/cache
- Layout:
  - app shell with sidebar, header, and main workspace
- Features (phases):
  - F1–F3: scaffold + query workbench + catalog explorer
  - F4: ingestion UI (local path + upload)
  - F5: copilot UI
  - F6: query history, favorites, and persistent named snippets with compare snapshots
  - F7: result UX (table/plan/debug viewers, charting)
  - F8: observability (debug metadata summary, benchmark viewer)
  - F9: polish (shortcuts, responsive layout, README, demo screenshots)

Details for frontend behavior and phases live in `frontend/README.md` and `todo.md`. When you change backend contracts, update those files alongside this one.

---