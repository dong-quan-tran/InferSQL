# InferSQL

InferSQL is a Python-based analytical SQL backend with a schema-aware LLM copilot.

It focuses on:

- A **DataFusion-backed analytical SQL engine** over Arrow-backed datasets.
- A **FastAPI** backend for SQL validation, planning, and execution.
- A guarded **natural-language-to-SQL copilot** with pluggable LLM providers (Ollama, Gemini, OpenAI).
- A small but growing set of **observability and benchmark hooks** suitable for turning into a full tracing/logging story.

The long-term vision is closer to internal infra at a quant/AI-native company than a typical CRUD app: a compact analytical engine, a catalog and ingestion layer, a feature/inference slice, and a copilot sitting safely on top.

---

## Current capabilities

### Engine and API surface

InferSQL is no longer a narrow custom engine; the real execution model is **DataFusion-centric** with a hybrid planning path:

- `/query/execute` uses DataFusion as the primary execution engine for the tested SQL surface.
- `/query/plan` is hybrid:
  - simple single-table queries may still use the legacy custom planner,
  - broader SQL (joins, subqueries, set operations) is planned via DataFusion explain output.
- `/query/validate` is a product-owned precheck layer built on SQLGlot and registry metadata.

The backend exposes:

- `POST /query/validate`  
  Product-level parse and validation. Returns:

  - `is_valid`, `query_type`
  - tables and columns referenced
  - flags such as `has_where`, `has_group_by`, `has_order_by`, `has_limit`
  - optional `debug` metadata when `debug=true`

- `POST /query/plan`  
  Planning artifacts. Returns:

  - original and normalized SQL
  - engine (`"infersql-planner"` or `"datafusion"`)
  - logical and physical plan representations (custom for simple queries, DataFusion explain for broad queries)
  - optional `debug` metadata

- `POST /query/execute`  
  End-to-end query execution. Returns:

  - `row_count`, `columns`, `rows`
  - optional logical/physical plan summaries where available
  - optional `debug` metadata (timings, engine, stage, features)

All three endpoints share:

- a common validation layer,
- a shared dataset registry,
- a normalized error model,
- a consistent `debug` object shape when `debug=true`.

The **exact tested SQL surface** and behavior of each endpoint are documented in `DEVELOPMENT.md`.

### Dataset registry and catalog

InferSQL uses an in-memory **dataset registry** as the source of truth for what is queryable:

- Apache Arrow tables are registered in `DatasetRegistry`.
- The registry owns dataset names, schemas, optional descriptions, column metadata, and basic source metadata.

Current catalog/ingestion endpoints:

- `GET /catalog/datasets` – list all registered datasets with metadata.
- `GET /catalog/datasets/{name}` – detailed metadata for a single dataset (schema, row count, descriptions, optional samples).
- `POST /catalog/ingest` – ingest CSV/Parquet from a local path and register it.
- `POST /catalog/upload` – ingest CSV/Parquet from an uploaded file via a temporary write + shared ingestion path.

Once a dataset is registered in the registry, it is immediately available to `/query/execute`.

If a dataset or column is not present in the registry, product validation treats it as unknown and queries fail with normalized errors.

### Copilot

InferSQL includes a schema-aware, validation-first copilot layer built on top of the same registry and query service used by the core engine.

**Provider abstraction**

- Pluggable LLM provider interface with:

  - Ollama backend (local-first, default for development).
  - Gemini backend (`google-genai`).
  - OpenAI backend (official `openai` client).

- Provider factory:

  - `llm_provider` setting supports `ollama`, `gemini`, `openai`, and `auto`.
  - `auto` uses configuration to select a primary provider while keeping Ollama as a fallback.
  - A fallback provider can wrap a primary provider with an Ollama fallback on provider errors.

**Schema awareness and prompting**

- A prompt builder that:

  - produces strict “JSON-only, SELECT-only SQL” system prompts,
  - injects synonym guidance (e.g., `ticker → symbol`, `stock price → close`),
  - includes a JSON schema for the expected `CopilotSqlCandidate` shape,
  - uses registry-backed schema context (tables, columns, descriptions, samples).

- Schema selection:

  - a schema selector scores tables based on names, descriptions, columns, and sample values,
  - simple normalization for singular/plural names,
  - synonym rules for better matching,
  - returns a small set of relevant tables.

- Schema context:

  - a context builder renders human-readable schema snippets for the LLM,
  - content is aligned with what catalog endpoints and validation use.

**Validation and repair loop**

`CopilotService` coordinates the flow:

1. Build schema context from `DatasetRegistry`.
2. Call an `LLMProvider` to produce a `CopilotSqlCandidate` (JSON).
3. Validate the candidate via the same query service path backing `/query/validate` and `/query/execute`.
4. If invalid, construct a repair prompt with:

   - original question,
   - schema context,
   - previous SQL and validation errors.

5. Retry up to a configured maximum.
6. Return a structured `CopilotQueryResponse` including:

   - final SQL candidate,
   - validation shape (tables, columns, flags),
   - optional execution result (if execution was requested),
   - retry/repair metadata.

**Eval harness**

The copilot has a dedicated evaluation harness:

- deterministic fake LLM provider (`EvalLLMProvider`),
- deterministic fake query service (`EvalQueryService`),
- cases covering:

  - simple selects,
  - synonyms and schema mismatch repair,
  - hallucinated datasets/columns and unsupported features,
  - joins and aggregates that should succeed,
  - subqueries and set operations.

- per-category metrics and a summary with minimum pass-rate thresholds.

A separate script can run live evals against a real LLM provider (e.g., Ollama) using the same cases.

---

## Error model and debug flag

All query endpoints return a **normalized error envelope** on non-2xx responses:

```json
{
  "error": {
    "type": "UnknownDatasetError",
    "code": "UNKNOWNDATASETERROR",
    "message": "Unknown dataset 'fundamentals'",
    "status_code": 404,
    "request_id": "b9fc0a0e-...",
    "debug": {
      "stage": "execute",
      "engine": "datafusion",
      "error_origin": "engine_execution"
    }
  }
}
```

- `type` – error type (e.g., `InvalidQuerySyntaxError`, `UnknownDatasetError`, `UnknownColumnError`, `UnsupportedQueryError`, `InternalServerError`).
- `code` – uppercased version for logs and client-side branching.
- `message` – human-readable description.
- `status_code` – HTTP status.
- `request_id` – correlation ID for logs and traces.

The optional `debug` object is included when `debug=true` and carries:

- `stage` – `"validate"`, `"plan"`, `"execute"`, or `"error"`.
- `engine` – `"datafusion"`, `"infersql-planner"`, or `null` where applicable.
- `error_origin` – coarse origin classifier such as `"engine_execution"`.

The flag is meant for internal/local use, not exposed to untrusted production clients.

---

## Configuration

Configuration is handled by a Pydantic `Settings` model, loaded once at startup and attached to the app.

Broad groups:

- **Core app**

  - `app_name`, `app_version`, `environment`.

- **Logging & observability**

  - `log_json`, `log_level`.
  - `service_name` for tracing resources.
  - toggles for OTEL exporters.

- **Datasets**

  - options to seed demo datasets at startup (e.g., `prices`, `fundamentals`).

- **LLM / copilot**

  - `llm_provider` (`ollama`, `gemini`, `openai`, `auto`).
  - `llm_temperature`.
  - provider-specific configuration (base URLs, models, API keys).

---

## Running the backend locally

From the `backend/` directory:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Run the API (dev)
uvicorn app.main:app --reload
```

By default, the app:

- loads settings from environment variables / `.env`,
- seeds demo datasets when configured,
- exposes `/query`, catalog, and copilot endpoints.

Once running, you can:

- use `/docs` for interactive OpenAPI docs,
- call `/query/validate`, `/query/plan`, `/query/execute` for SQL workloads,
- call copilot endpoints for NL→SQL experiments (with an LLM provider configured).

---

## Registering datasets

InferSQL can only query datasets that are registered in the dataset registry.

### Ingest from a local path

Example: ingest a CSV file at `data/prices.csv` as a dataset named `prices`:

```bash
curl -X POST http://localhost:8000/catalog/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prices",
    "path": "data/prices.csv",
    "description": "Daily prices dataset"
  }'
```

### Upload and ingest

Example: upload a local `fundamentals.parquet` file:

```bash
curl -X POST http://localhost:8000/catalog/upload \
  -H "Content-Type: multipart/form-data" \
  -F "file=@fundamentals.parquet" \
  -F "name=fundamentals" \
  -F "description=Fundamentals dataset"
```

### Inspect datasets

List all registered datasets:

```bash
curl http://localhost:8000/catalog/datasets
```

Inspect a single dataset:

```bash
curl http://localhost:8000/catalog/datasets/prices
```

---

## Query workflow

Think of the three main endpoints as:

- `/query/validate` – precheck, shape summary, and product guardrails.
- `/query/plan` – planning artifacts (logical/physical plans).
- `/query/execute` – execution with optional debug metadata.

### Validate a query

```bash
curl -X POST http://localhost:8000/query/validate \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
  }'
```

### Plan a query

```bash
curl -X POST http://localhost:8000/query/plan \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
  }'
```

### Execute a query (with debug)

```bash
curl -X POST "http://localhost:8000/query/execute?debug=true" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
  }'
```

---

## What “broad SQL” means (today)

“Broad SQL” here means a **tested, DataFusion-backed analytical subset**, not full ANSI SQL.

In practice, the currently documented surface includes support for:

- `SELECT`-only queries (no DML/DDL).
- Single-table and multi-table queries over registered datasets.
- Joins (e.g., `INNER`, `LEFT`) where tests exist.
- Subqueries:
  - `IN (subquery)`,
  - subqueries in `FROM`,
  - scalar subqueries in `SELECT` and `WHERE`.
- Set operations:
  - `UNION`,
  - `UNION ALL` (with shape checks).
- Projected expressions and aliases in `SELECT`.
- `WHERE` filters with common comparisons.
- `ORDER BY` on projected or queryable columns.
- `LIMIT` (with offset as supported).
- Aggregates:
  - `COUNT`, `SUM`, `AVG`, etc.,
  - grouped aggregates and `HAVING` for tested shapes.
- Normalized error behavior for syntax errors, unknown datasets/columns, ambiguous references, and unsupported semantics.

The precise surface is intentionally narrower than DataFusion’s full capability and is defined by tests and documented in `DEVELOPMENT.md`.

---

## Concrete SQL examples

Assuming `prices` and `fundamentals` are registered:

### Join

```sql
SELECT p.symbol, p.close, f.metric
FROM prices AS p
JOIN fundamentals AS f
  ON p.symbol = f.symbol
WHERE p.close > 100
ORDER BY p.close DESC
LIMIT 10;
```

### Subquery

```sql
SELECT symbol, close
FROM prices
WHERE symbol IN (
  SELECT symbol
  FROM fundamentals
)
ORDER BY close DESC
LIMIT 10;
```

### HAVING

```sql
SELECT symbol, AVG(close) AS avg_close
FROM prices
GROUP BY symbol
HAVING AVG(close) > 100
ORDER BY avg_close DESC
LIMIT 10;
```

### UNION

```sql
SELECT symbol FROM prices
UNION
SELECT symbol FROM fundamentals;
```

### Copilot NL→SQL example

Natural language:

> Show me the symbols and closing prices above 100, highest price first, limited to 5.

Possible SQL candidate:

```sql
SELECT symbol, close
FROM prices
WHERE close > 100
ORDER BY close DESC
LIMIT 5;
```

The copilot layer generates candidates of this form, validates them via the query service, and can optionally execute them.

---

## Performance benchmark harness (Phase 12)

InferSQL includes a small, in-process benchmark harness for `/query/execute`.

The script lives at:

- `scripts/benchmark_queries.py`

It:

- starts the FastAPI app with lifespan so `app.state` services are initialized,
- seeds synthetic benchmark datasets into the in-memory registry:

  - `prices_bench_1000`
  - `prices_bench_10000`
  - `prices_bench_100000`
  - `prices_bench_1000000`

- each `prices_bench_*` has `symbol` (string) and `close` (float),
- each `fundamentals_bench_*` has `symbol` (string) and `metric` (float),

- runs the following query shapes at each row size:

  - filter + project + limit  
    `SELECT symbol, close FROM prices_bench_* WHERE close > 100 LIMIT 100`
  - grouped aggregate  
    `SELECT symbol, AVG(close) AS avg_close FROM prices_bench_* GROUP BY symbol`
  - order-by + limit  
    `SELECT symbol, close FROM prices_bench_* ORDER BY close DESC LIMIT 100`
  - join  
    `SELECT p.symbol, p.close, f.metric FROM prices_bench_* AS p JOIN fundamentals_bench_* AS f ON p.symbol = f.symbol WHERE p.close > 100`

- calls `/query/execute?debug=true` through an in-process ASGI client,
- records multiple iterations per workload,
- writes results to `benchmark_results/`:

  - `benchmark_summary_<RUN_ID>.json` – run metadata and per-workload summary stats (min/mean/median/p95/max).
  - `benchmark_summary_<RUN_ID>.csv` – tabular summary.
  - `benchmark_iterations_<RUN_ID>.csv` – per-iteration latencies.

### Running the benchmark

From the project root (with your virtualenv active):

```bash
python scripts/benchmark_queries.py
```

To establish a local baseline, you can copy a specific run’s summary files to stable names, for example:

```bash
copy benchmark_results\benchmark_summary_<RUN_ID>.json benchmark_results\benchmark_summary_phase12_baseline.json
copy benchmark_results\benchmark_summary_<RUN_ID>.csv  benchmark_results\benchmark_summary_phase12_baseline.csv
```

Future performance work should extend this script and update `DEVELOPMENT.md` as needed.

---

## Repository structure (backend)

This README focuses on the backend engine + copilot.

Relevant layout:

```text
backend/
  └── app/
      ├── api/
      │   ├── query.py          # /query endpoints
      │   ├── dependencies.py
      │   └── ...
      ├── core/
      │   ├── catalog/
      │   │   └── registry.py   # DatasetRegistry
      │   ├── engine/
      │   │   ├── parser.py
      │   │   ├── physical_planner.py
      │   │   └── ...
      │   ├── error_handlers.py
      │   ├── lifespan.py
      │   ├── middleware.py
      │   └── settings.py
      ├── schemas/
      └── services/
          ├── query_service.py
          ├── query_compiler.py
          ├── query_runner.py
          ├── copilot_service.py
          └── llm/
scripts/
  ├── benchmark_queries.py      # Phase 12 benchmark harness
  └── ...
tests/
  # Engine, API, copilot, and eval tests
```

For a deeper, architecture-level view of the platform and roadmap, see `Blueprint.md`. For detailed behavior of the SQL surface, registry, catalog, copilot, and benchmarks, see `DEVELOPMENT.md`.

---

## Status

InferSQL is actively evolving. The current focus is:

1. **Broad SQL core**  
   DataFusion-backed execution and hybrid planning for a clearly documented subset of analytical SQL.

2. **Catalog and ingestion**  
   CSV/Parquet ingestion wired into the registry and engine, plus catalog and schema inspection endpoints.

3. **Copilot and evals**  
   Schema-aware prompts, safer NL→SQL behavior, and an eval harness that tracks quality across categories.

4. **Observability and performance**  
   Consistent debug metadata, structured errors, an in-process benchmark harness, and the foundations for tracing and metrics.

Later phases will extend this foundation into a fuller feature store, inference slice, and observability stack built on top of the same query engine and registry.