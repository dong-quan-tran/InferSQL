# InferSQL

InferSQL is a Python-based analytical SQL backend with a schema-aware text‑to‑SQL copilot. It exposes a FastAPI HTTP API and a React workbench UI for validating, planning, and executing SQL over Arrow‑backed datasets, with clear debug metadata, normalized errors, and a small benchmark harness.

## Quick start

### Requirements

- Python 3.10+
- Git
- Recommended: a virtual environment
- Optional: Docker for containerized runs
- Optional: an LLM provider (Ollama, Gemini, OpenAI) for the copilot

### 1. Clone the repository

```bash
git clone https://github.com/dong-quan-tran/InferSQL.git
cd InferSQL
```

### 2. Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows (cmd):

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

From the `backend/` directory:

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run backend tests

```bash
python -m pytest
```

Tests cover the query API (`/query/validate`, `/query/plan`, `/query/execute`), catalog and ingestion endpoints, copilot behavior, and the benchmark harness.

### 5. Start the API server

From `backend/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local endpoints:

- Base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

By default, the app loads settings from environment variables / `.env`, seeds demo datasets when configured, and exposes query, catalog, ingestion, and copilot endpoints.

## Frontend workbench

InferSQL includes a Vite + React + TypeScript workbench UI that sits on top of the backend.

From the `frontend/` directory:

```bash
cd ../frontend
npm install
npm run dev
```

Typical local frontend URL:

- `http://localhost:5173`

If needed, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Workbench features

The workbench is organized into a sidebar shell with views for:

- **Query workbench**
  - SQL editor (textarea‑based)
  - validate / plan / execute actions wired to backend endpoints
  - response panel for raw JSON, logical plan, physical plan, and debug metadata
  - result table with CSV export
  - lightweight charting for suitable aggregate results
  - session‑backed query history with favorites and load‑into‑editor
  - persistent named snippets with load/rename/delete/pin and basic compare snapshots

- **Catalog explorer**
  - dataset list backed by `/catalog/datasets`
  - detail view backed by `/catalog/datasets/{name}`
  - quick actions to insert example SQL into the editor

- **Copilot view**
  - NL→SQL prompt input
  - generated SQL candidates
  - assumptions and validation output
  - optional execution result
  - “send to editor” integration

A backend change to contracts (query, catalog, copilot, benchmarks) should be reflected in `frontend/README.md`, `todo.md`, and this README.

## Query API

InferSQL exposes a FastAPI query API built around a DataFusion‑backed engine and a hybrid planning path.

### Endpoints

- `POST /query/validate`
  Product‑owned parse and validation over the registry.

- `POST /query/plan`
  Planning artifacts (logical/physical plans) via a hybrid planner.

- `POST /query/execute`
  End‑to‑end query execution via DataFusion, with optional debug metadata.

All three endpoints share a common validation layer, a shared dataset registry, and a normalized error model.

### `POST /query/validate`

Request body:

```json
{
  "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
}
```

Example response (shape):

```json
{
  "sql": "...",
  "normalized_sql": "...",
  "is_valid": true,
  "query_type": "SELECT",
  "tables": ["prices"],
  "columns": ["symbol", "close"],
  "has_where": true,
  "has_group_by": false,
  "has_order_by": true,
  "has_limit": true,
  "errors": [],
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

`is_valid` reflects product‑level validation only; a query can pass validate but still fail execute if engine‑level semantics are violated.

### `POST /query/plan`

Request body:

```json
{
  "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
}
```

Example behavior:

- Simple single‑table queries:
  - use the legacy custom planner
  - return `engine: "infersql-planner"`
  - include custom `logical_plan` and `physical_plan` nodes

- Broader SQL (joins, subqueries, unions):
  - delegate to DataFusion explain output
  - wrap explain lines into structured `logical_plan` and `physical_plan` nodes
  - set `engine: "datafusion"`

Debug metadata is included when `debug=true` in the query string.

### `POST /query/execute`

Request body:

```json
{
  "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
}
```

Example response (shape):

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
  "logical_plan": null,
  "physical_plan": null,
  "debug": {
    "request_id": "...",
    "total_ms": 3.21,
    "stage": "execute",
    "engine": "datafusion",
    "error_origin": null,
    "features": ["join"]
  }
}
```

Logical and physical plans are populated where available and meaningful. The frontend surfaces this as:

- a JSON view showing the full response
- a tabular view for `columns` + `rows`
- optional plan/debug tabs

## Dataset registry and catalog

InferSQL uses an in‑memory dataset registry as the source of truth for what is queryable.

### Catalog endpoints

- `GET /catalog/datasets`
  List all registered datasets with:
  - name, description, row count, source path, loaded timestamp
  - column names, types, and optional column descriptions

- `GET /catalog/datasets/{name}`
  Single dataset detail:
  - same metadata as the list endpoint
  - optional column samples and aliases

- `POST /catalog/ingest`
  Ingest CSV/Parquet from a local path:
  - CSV via `pyarrow.csv.read_csv`
  - Parquet via `pyarrow.parquet.read_table`
  - register the resulting Arrow table in the registry

- `POST /catalog/upload`
  Upload CSV/Parquet:
  - write the upload to a temporary file
  - reuse the same ingestion path as `/catalog/ingest`

Once a dataset is registered, it is immediately available to `/query/execute`. If a dataset or column is not present in the registry, validation treats it as unknown and queries fail with normalized errors.

## Copilot

InferSQL includes a schema‑aware, validation‑first text‑to‑SQL copilot built on top of the registry and query service.

### Provider abstraction

Pluggable LLM provider interface with:

- Ollama backend (local‑first, default for development)
- Gemini backend (Google GenAI)
- OpenAI backend (official client)

A provider factory:

- reads a provider setting (e.g., `ollama`, `gemini`, `openai`, `auto`)
- constructs the appropriate provider with base URL, model, and temperature
- can wrap providers with a fallback (e.g., Ollama as backup)

### Schema awareness and prompting

Copilot uses:

- a prompt builder that:
  - enforces `SELECT`‑only queries
  - injects registry‑backed schema context and synonym guidance
  - returns a structured `CopilotSqlCandidate` JSON object

- a schema selector that:
  - scores tables based on names, descriptions, columns, and samples
  - applies simple singular/plural normalization and synonyms
  - picks a small set of relevant datasets

### Validation and repair loop

`CopilotService` orchestrates:

1. Build schema context from the registry.
2. Call an `LLMProvider` to produce a `CopilotSqlCandidate`.
3. Validate the candidate via the same query path used by `/query/validate` and `/query/execute`.
4. If invalid, construct a repair prompt with question, schema, SQL, and errors.
5. Retry up to a configured maximum.
6. Return a structured response with:
   - final SQL candidate
   - validation shape (tables, columns, flags, errors)
   - optional execution result
   - repair metadata

### Eval harness

InferSQL includes an eval harness for copilot behavior:

- deterministic fake LLM provider
- deterministic fake query service
- eval cases for simple selects, synonyms, joins, aggregates, subqueries, and unsupported features
- per‑category metrics and minimum pass‑rate thresholds
- a separate script to run live evals against a real provider using the same cases

## Error model and debug metadata

Query endpoints use a normalized error envelope on non‑2xx responses:

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

Core fields:

- `type` – normalized error type
- `code` – uppercased code for logs/branching
- `message` – human‑readable description
- `status_code` – HTTP status
- `request_id` – correlation ID
- `debug` – optional debug metadata (stage, engine, error_origin, features)

This structure is intended for internal/local use and observability; public clients can ignore the debug object if not needed.

## Performance benchmark harness

InferSQL includes a small, in‑process benchmark harness for `/query/execute`.

Script location:

- `scripts/benchmark_queries.py`

It:

- starts the FastAPI app with lifespan
- seeds synthetic Arrow‑backed benchmark datasets into the registry (e.g., `prices_bench_*`, `fundamentals_bench_*` at multiple row sizes)
- runs representative query shapes:
  - filter + project + limit
  - grouped aggregate
  - order‑by + limit
  - join
- calls `/query/execute?debug=true` via an ASGI client
- records multiple iterations per workload
- writes JSON and CSV artifacts to `benchmark_results/`

### Running the benchmark

From the project root (virtualenv active):

```bash
python scripts/benchmark_queries.py
```

You can copy a specific run’s summary files to stable names (e.g., `benchmark_summary_phase12_baseline.json`) to establish a local baseline.

## Project structure

Backend‑focused layout:

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
tests/
frontend/
  └── ...
```

High‑level responsibilities:

- `app/api/query.py` — HTTP routes for validate, plan, execute, and catalog/ingestion
- `app/core/catalog/registry.py` — dataset registry and metadata
- `app/core/engine/` — parser, physical planner, and engine integration
- `app/services/query_service.py` — orchestration of validation, planning, and execution
- `app/services/copilot_service.py` — copilot orchestration and repair loop
- `scripts/benchmark_queries.py` — performance harness
- `frontend/` — React workbench UI
- `tests/` — pytest suite for engine, API, copilot, and benchmarks

## Testing

From `backend/`:

```bash
python -m pytest
```

You can run focused files as needed, for example:

```bash
python -m pytest tests/test_query_validate.py -q
python -m pytest tests/test_query_execute.py -q
python -m pytest tests/test_copilot_eval.py -q
```

## Roadmap

Near‑term focus:

- stronger coverage for broad analytical SQL in tests and docs
- richer schema inspection endpoints and catalog UX
- more robust copilot evals and prompt tuning
- extended benchmark workloads and better debug/observability hooks in the frontend

InferSQL is intended as a compact, inspectable analytical SQL + copilot platform that can grow into a more complete internal data/AI plane over time.

## Author

InferSQL is developed and maintained by:

- **Dong Quan Tran (Johnny)**
- Role: Owner / Collaborator
- Email: dxt9721@mavs.uta.edu / dongquan.tran.johnny@gmail.com
- GitHub: dong-quan-tran