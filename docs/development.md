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
- API tests for catalog and ingestion,
- smoke tests for copilot and catalog integration.

## Migration status

InferSQL has migrated from a custom narrow SQL path to a hybrid architecture centered on Apache DataFusion.

Current state:

- `/query/execute` is DataFusion-backed for production query execution across the supported SQL surface.
- `/query/plan` is hybrid:
  - simple single-table queries may still use the legacy custom planner,
  - broader SQL shapes such as joins, subqueries, and set operations are planned through DataFusion.
- `/query/validate` remains product-owned:
  - it uses SQLGlot plus registry metadata for schema checks and guardrails,
  - it is not the final source of semantic SQL truth.
- The original custom engine remains as a narrow planning/reference layer; it is no longer the primary execution engine.

Practical meaning:

- broad SQL capability should be judged by tested `/query/execute` behavior and broad `/query/plan` behavior,
- not by legacy single-table assumptions from the original planner.

## Current SQL surface (developer view)

InferSQL currently supports a **broad but explicit analytical SQL subset** over registered datasets. DataFusion provides the underlying execution and planning engine; InferSQL exposes the subset that is tested and integrated with product validation.

This file is the ground truth for what is **actually supported and tested**.

## Registry and metadata

InferSQL uses the dataset registry as the source of truth for dataset metadata.

The registry owns:

- dataset names,
- Arrow-backed column names and column types,
- optional dataset descriptions,
- optional column descriptions,
- source metadata such as `source_path` and `loaded_at`,
- optional sample values exposed through catalog detail responses.

Other layers derive schema information from the registry rather than maintaining separate schema definitions:

- catalog endpoints serialize registry-backed metadata,
- query validation checks datasets and columns against registry schemas,
- query execution runs only against datasets that are registered.

If a dataset is not present in the registry, it is not queryable.  
If a column is not present in the registry schema for that dataset, it should be treated as unknown.

### Dataset naming conventions

Registered dataset names should follow these conventions:

- lowercase only,
- snake_case,
- ASCII letters, digits, and underscores only,
- stable names once exposed through the API.

Recommended examples:

- `prices`
- `prices_nulls`
- `fundamentals`
- `daily_trades`

Avoid:

- spaces (`"stock prices"`),
- hyphens (`"stock-prices"`),
- mixed case (`"Prices"`),
- environment-specific suffixes in public names unless they are part of the intended contract.

Column names should also be lowercase snake_case where possible.

## Catalog and ingestion

InferSQL exposes a catalog and ingestion API backed by the dataset registry:

- `/catalog/datasets` lists all registered datasets with:
  - name, description, row count, source path, loaded timestamp,
  - column names, types, and optional column descriptions.
- `/catalog/datasets/{name}` returns a single dataset detail, including:
  - the same metadata as the list endpoint,
  - optional column samples and column aliases.
- `/catalog/ingest` ingests a dataset from a local path:
  - supports CSV (`.csv`) via `pyarrow.csv.read_csv`,
  - supports Parquet (`.parquet`) via `pyarrow.parquet.read_table`,
  - registers the resulting `pa.Table` in the registry with:
    - schema,
    - row count,
    - `source_path`,
    - `loaded_at`,
    - optional dataset description.
- `/catalog/upload` ingests a dataset from an uploaded file:
  - supports CSV and Parquet uploads,
  - writes the upload to a temporary file,
  - then reuses the same ingestion path as `/catalog/ingest`.

Ingestion rules:

- duplicate dataset names:
  - rejected by default with a `409 Conflict`,
  - allowed when `overwrite=true`, in which case the dataset is replaced.
- unsupported file formats:
  - rejected as `400 ValidationError` with `UnsupportedDatasetFormatError`.
- missing or unreadable files, malformed CSV, and invalid Parquet:
  - rejected as `400 ValidationError` via a normalized `DatasetLoadError`.

Newly ingested datasets are immediately queryable via `/query/execute` once they are registered in the registry.

### Supported (high-level)

- `SELECT` queries only (no DML/DDL).
- Single-table and multi-table queries over registered datasets.
- Joins:
  - `INNER JOIN`,
  - `LEFT JOIN`,
  - additional join patterns where tests exist.
- Subqueries:
  - `IN (subquery)`,
  - subqueries in `FROM` (derived tables),
  - scalar subqueries in `SELECT`,
  - scalar subqueries in `WHERE`.
- Set operations:
  - `UNION`,
  - `UNION ALL`,
  - column-count and type compatibility enforced by the engine.
- Projection:
  - plain column projection,
  - projection aliases,
  - arithmetic and other tested expressions in `SELECT`.
- `WHERE` filters:
  - column-vs-literal comparisons (e.g., `=`, `!=`, `<`, `<=`, `>`, `>=`),
  - tested expressions in `WHERE`.
- `ORDER BY`:
  - on projected or queryable columns,
  - on raw expressions where tested,
  - `ASC` and `DESC`.
- `LIMIT` (with offset).
- Aggregates:
  - basic aggregates such as `COUNT`, `SUM`, `AVG`,
  - grouped aggregation,
  - `HAVING` over tested grouped queries.
- Basic support for **normalized error behavior**:
  - syntax errors,
  - unknown datasets,
  - unknown columns,
  - ambiguous/unqualified columns across multiple datasets,
  - unsupported or invalid semantics mapped to `UnsupportedQueryError`.

### Validation vs engine responsibilities

Product-level validation (using SQLGlot and registry metadata) is responsible for:

- enforcing allowed statement types (`SELECT`),
- ensuring referenced datasets exist in the registry,
- ensuring referenced columns exist on those datasets,
- detecting ambiguous unqualified columns across multiple datasets,
- enforcing a small number of product guardrails, including rejection of `SELECT *` with `GROUP BY` for single-table queries.

DataFusion is responsible for:

- full semantic correctness of:
  - join semantics,
  - grouped aggregates,
  - `HAVING`,
  - subqueries,
  - set operations,
  - expression legality,
- query planning and execution correctness.

The rule of thumb:

- `/query/validate` is a **precheck**:
  - enforces `SELECT`-only,
  - checks datasets and columns against the registry,
  - applies the single-table `SELECT *` with `GROUP BY` guardrail,
  - does not attempt to re-implement engine-level grouped/aggregate/window semantics.
- `/query/execute` and broad `/query/plan` treat DataFusion as the source of truth for SQL semantics and only normalize errors into product types.

### Current `/query/validate` behavior

`POST /query/validate`:

- Accepts a JSON body with `sql`.
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

  - uses the legacy custom planner,
  - returns `engine: "infersql-planner"`,
  - returns custom `logical_plan` and `physical_plan` nodes.

- For broader SQL (joins, subqueries, unions):

  - delegates to DataFusion planning and explain output to obtain logical and physical plans,
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

  - sets `engine: "datafusion"`.

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

- Applies the same product-level schema and guardrail validation used by `/query/validate`, then executes via DataFusion.
- Returns:

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
      "error_origin": "engine_execution"
    }
  }
}
```

The mapping is:

- parse or syntax issues → `InvalidQuerySyntaxError` (400),
- unknown table or dataset → `UnknownDatasetError` (typically 404),
- unknown column → `UnknownColumnError` (400),
- unsupported semantics or ambiguous references → `UnsupportedQueryError` (currently treated as a client error where normalized),
- unexpected internal engine failures → 5xx internal error responses via `InternalServerError`.

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
  - advanced statistics-based planning.

If you are unsure whether a feature is supported:

- search for a test in `tests/test_query_execute.py` or `tests/test_query_plan.py`,
- if no test exists, treat the feature as unsupported until one is added.

## Developer guidelines

- **Add tests first** for any new SQL surface you intend to support.
- **Update this file** whenever you expand or restrict the supported SQL subset or change catalog/ingestion behavior.
- Keep `/query/validate`, `/query/plan`, and `/query/execute` behavior in sync by reusing validation helpers.
- Keep the documented SQL surface tied to tested behavior, not aspirational claims.
- When in doubt, prefer:
  - precise errors,
  - explicit non-support,
  - clear documentation over silent behavior changes.

## Copilot and eval harness

InferSQL includes a small, self-contained copilot layer that generates SQL candidates from natural language questions over the registered datasets. The copilot flow is fully test-backed and designed to support multiple LLM providers without hard-wiring to any specific API.

### Copilot architecture (developer view)

- `CopilotService` owns the high-level query flow:
  - builds schema context from the dataset registry,
  - calls an `LLMProvider` to generate a `CopilotSqlCandidate`,
  - validates the candidate via the query service (`/query/validate` behavior),
  - optionally executes the candidate via the query service (`/query/execute` behavior),
  - returns a structured result with validation, execution (optional), and candidate metadata.
- `LLMProvider` is the common interface for all LLM backends. Concrete implementations live in `app.services.llm.*`:
  - `OllamaLLMProvider` is the default local provider and has no paid dependencies.
  - `GeminiLLMProvider` and `OpenAILLMProvider` are optional:
    - they use lazy imports (`google-genai`, `openai`) inside `__init__`,
    - they are only required if you choose those providers and install the corresponding SDKs.
- `build_llm_provider` in `app.services.llm.factory` centralizes provider selection:
  - reads a provider name (e.g. `ollama`, `gemini`, `openai`, `auto`),
  - constructs the appropriate provider with configuration such as base URL, model name, and temperature,
  - wraps primary providers in a `FallbackLLMProvider` so Ollama is always available as a fallback when configured.

This provider abstraction means you can add or switch LLM backends without changing `CopilotService` or the rest of the API layer; only the factory configuration and dependencies need to change.

### Copilot prompts

Copilot uses a prompt builder that is explicitly aligned with the tested broad SQL surface and structured-output requirements:

- `build_system_prompt`:
  - instructs the model to:
    - generate only `SELECT` queries over registered datasets,
    - use a broad but explicit analytical SQL subset (joins, grouped aggregates, `HAVING`, subqueries, set operations),
    - ground all references in the provided schema context (no invented tables, columns, or join keys),
    - qualify columns in multi-table queries when ambiguity is possible,
    - map business synonyms (e.g. “ticker”, “price”) to canonical schema columns when supported and record those mappings in `assumptions`,
    - choose conservative interpretations for ambiguous questions (e.g. “latest”, “best”) and document limitations in `assumptions`,
    - return exactly one JSON object that matches the `CopilotSqlCandidate` schema (no prose, no markdown fences, no extra keys).
- `build_user_prompt`:
  - injects registry-backed schema context, synonym guidance, and few-shot examples,
  - explains how to:
    - prefer the smallest valid query that answers the question,
    - use joins only when necessary and with explicit join conditions grounded in the schema,
    - use grouped aggregates and `HAVING` when appropriate,
    - use subqueries (`IN`, scalar, derived tables) when needed,
    - repair schema mismatches and ambiguity via explicit `assumptions` rather than silent changes.

Together, these prompts enforce a structured-output contract for Copilot and make the behavior match the eval harness’s expectations.

### Copilot evals (Phase 9)

Phase 9 migrated Copilot from a narrow, single-table world to a tested **broad SQL** surface aligned with the DataFusion-backed architecture:

- The eval harness now covers:
  - simple single-table projections and filters,
  - synonym and schema-mismatch repair (e.g. `ticker` → `symbol`, `price` → `close`),
  - hallucinated datasets/columns and unsupported features,
  - aggregate queries with `COUNT`/`AVG` and `HAVING` on grouped results,
  - successful joins between `prices` and `fundamentals`,
  - successful subqueries over the richer registry (e.g. `IN (SELECT symbol FROM fundamentals)`, scalar subqueries for overall aggregates).
- Eval cases are grouped into categories such as:
  - `simple_select`,
  - `synonym`,
  - `hallucination`,
  - `unsupported_feature`,
  - `ambiguous`,
  - `aggregate`,
  - `join`,
  - `subquery`.

Copilot behavior is covered by a dedicated eval harness and two entry points:

- `tests/test_copilot_eval.py`:
  - uses `EvalLLMProvider`, a fake provider that returns deterministic `CopilotSqlCandidate` objects based on the original question,
  - uses `EvalQueryService`, a fake query service that:
    - normalizes SQL and inspects it for known patterns,
    - simulates product behavior for:
      - valid single-table queries on the `prices` dataset,
      - joins and aggregates that are expected to succeed,
      - unknown datasets (`trades`), unknown columns (`ticker`, `price`, `sector`), and unsupported semantics,
    - returns a validation shape compatible with `/query/validate` and `/query/execute`.
  - loads eval cases from `tests/fixtures/copilot_eval_cases.json`. Each case defines:
    - an `id` and `category`,
    - a natural-language `question`,
    - whether execution should be attempted (`execute`),
    - expectations for validity, columns, row counts, SQL fragments, error messages, and assumptions.
  - includes:
    - a parametrized test that asserts each case individually, and
    - a suite summary test that builds category-level metrics and enforces minimum pass-rate thresholds, including 100% for critical categories like `simple_select`, `hallucination`, `unsupported_feature`, and `join`.
- `scripts/run_copilot_live_eval.py`:
  - runs the same `CopilotService` flow against a real `LLMProvider` (typically Ollama in local development),
  - uses Arrow-backed `prices` and `fundamentals` tables registered through `DatasetRegistry`,
  - reuses the same eval cases and assertion logic as the unit tests,
  - prints a JSON summary including:
    - provider name and model,
    - overall pass rate,
    - per-category pass rates,
    - details for failing cases (question, generated SQL, assumptions, validation errors).
  - enforces configurable thresholds so you can fail a CI job or local check if regressions occur.

As you broaden the SQL surface area that Copilot should reliably handle beyond Phase 9, the workflow is:

1. Add new eval cases (and extend `EvalQueryService` where needed) to cover the desired behavior.
2. Tune prompts or providers until the eval suite and live eval both pass at the desired thresholds.
3. Update this file and `todo.md` to document the new supported surface.

### Copilot evals only

To run just the copilot eval tests:

```bash
python -m pytest tests/test_copilot_eval.py
```

To run the live copilot eval script (Ollama-only by default):

```bash
COPILOT_LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1 \
python scripts/run_copilot_live_eval.py
```

## Performance benchmarks (Phase 12)

Phase 12 adds a small, repeatable performance harness that exercises `/query/execute` against synthetic Arrow tables registered in the in-memory dataset registry.

- The benchmark script lives at `scripts/benchmark_queries.py`.
- It seeds four synthetic benchmark datasets into the live registry (in-memory only):

  - `prices_bench_1000`
  - `prices_bench_10000`
  - `prices_bench_100000`
  - `prices_bench_1000000`

- Each `prices_bench_*` table has:

  - `symbol` (string): synthetic stock symbol (e.g. `SYM000001`),
  - `close` (float): synthetic closing price.

- Each `fundamentals_bench_*` table has:

  - `symbol` (string): synthetic stock symbol,
  - `metric` (float): synthetic metric value.

The script runs the following query shapes against each row size:

- `filter_project_limit`:
  - `SELECT symbol, close FROM prices_bench_* WHERE close > 100 LIMIT 100`
- `aggregate_group_by`:
  - `SELECT symbol, AVG(close) AS avg_close FROM prices_bench_* GROUP BY symbol`
- `order_by_limit`:
  - `SELECT symbol, close FROM prices_bench_* ORDER BY close DESC LIMIT 100`
- `join`:
  - `SELECT p.symbol, p.close, f.metric FROM prices_bench_* AS p JOIN fundamentals_bench_* AS f ON p.symbol = f.symbol WHERE p.close > 100`

Each workload is executed multiple times against the ASGI app in-process, using the same dataset registry instance that was seeded at runtime.

### Running the benchmark

From an activated virtual environment with dependencies installed:

```bash
python scripts/benchmark_queries.py
```

The script:

- wraps the FastAPI app in a lifespan-aware context so startup/shutdown hooks run and populate `app.state` services,
- seeds the synthetic benchmark datasets into the in-memory registry,
- runs all workloads against `/query/execute?debug=true`,
- records per-iteration latency and summary statistics,
- writes results into `benchmark_results/`.

Artifacts include:

- `benchmark_results/benchmark_summary_<RUN_ID>.json`:
  - run metadata (Python version, platform, commit, etc.),
  - one summary object per workload (query shape, row count, SQL, min/mean/median/p95/max latency, sample row count).
- `benchmark_results/benchmark_summary_<RUN_ID>.csv`:
  - tabular summary suitable for spreadsheets.
- `benchmark_results/benchmark_iterations_<RUN_ID>.csv`:
  - per-iteration latency records for detailed analysis.

To establish or update a local baseline, you can copy a specific run’s summary files to stable names, for example:

```bash
copy benchmark_results\benchmark_summary_<RUN_ID>.json benchmark_results\benchmark_summary_phase12_baseline.json
copy benchmark_results\benchmark_summary_<RUN_ID>.csv  benchmark_results\benchmark_summary_phase12_baseline.csv
```

Future performance work should:

- keep using this script as the canonical latency harness for `/query/execute`,
- extend it with additional workloads only when they are representative and stable,
- document any new workloads or dataset shapes here.