# InferSQL

InferSQL is a full-stack analytical SQL platform that combines Apache Arrow and DataFusion with a guarded, schema-aware text-to-SQL Copilot. It exposes FastAPI APIs and a React workbench for validating, planning, and executing read-only analytical SQL over in-memory Arrow datasets.

## Highlights

- Built on Apache Arrow, DataFusion, SQLGlot, FastAPI, Python, React, and TypeScript.
- Supports filtering, projections, ordering, limits, grouped aggregates, `HAVING`, joins, subqueries, derived tables, `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT`.
- Provides a local-first text-to-SQL Copilot using Ollama, with optional Gemini and OpenAI providers.
- Guards generated SQL with schema grounding, read-only intent checks, SQL parsing, schema validation, bounded repair retries, and execution only after validation.
- Achieved 33/33 execution-equivalent passes on a curated production-backed Copilot evaluation using local `llama3.1:8b`, SQLGlot validation, and DataFusion execution.
- Recorded 1M-row median query latencies of 6.7 ms for filter/project/limit, 8.9 ms for order-by/limit, 45.3 ms for grouped aggregation, and 44.6 ms for a filtered join in a 20-iteration in-process API benchmark.

> Benchmark and evaluation results are controlled local measurements, not cloud-production throughput claims. The Copilot evaluation uses a small, curated two-table schema; its score should be interpreted within that scope.

## Architecture

```text
Natural-language question
        |
        v
Intent guard -> schema selector -> schema-context builder
        |
        v
LLM provider (Ollama by default; Gemini/OpenAI optional)
        |
        v
Structured SQL candidate + assumptions
        |
        v
SQLGlot parsing + read-only validation + schema validation
        |
        +--> Block / clarify / bounded repair retry
        |
        v
DataFusion logical planning and Arrow-backed execution
        |
        v
FastAPI response: SQL, rows, plans, assumptions, retries, and debug metadata
```

## Quick start

### Requirements

- Python 3.10+
- Git
- Recommended: virtual environment
- Node.js and npm for the React workbench
- Optional: Docker for containerized runs
- Optional: Ollama, Gemini, or OpenAI configuration for the Copilot

### Clone the repository

```bash
git clone https://github.com/dong-quan-tran/InferSQL.git
cd InferSQL
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install backend dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### Run tests

From `backend/`:

```bash
python -m pytest -q
```

The test suite covers query validation, planning, DataFusion execution, catalog behavior, Copilot orchestration, intent safety, schema validation, set operations, and evaluation utilities.

### Start the API

From `backend/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local endpoints:

- API base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

The application reads configuration from environment variables and `.env` when present. Demo datasets are seeded when `seed_demo_data=true`.

## Frontend workbench

InferSQL includes a Vite, React, and TypeScript workbench that uses the backend APIs.

From the project root:

```bash
cd frontend
npm install
npm run dev
```

The typical development URL is `http://localhost:5173`.

If needed, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Workbench features

- Query workbench with SQL editor, validate, plan, and execute actions
- Result tables with CSV export and lightweight charting for suitable aggregate output
- Logical-plan, physical-plan, raw JSON, and debug metadata views
- Session-backed query history, favorites, named snippets, and comparison snapshots
- Catalog explorer for datasets, columns, descriptions, aliases, and sample values
- Copilot view for natural-language questions, generated SQL, assumptions, validation, retries, execution output, and send-to-editor actions

## Query API

InferSQL exposes a FastAPI query API with a shared validation layer, dataset registry, normalized errors, and a hybrid planning path.

| Endpoint | Purpose |
|---|---|
| `POST /query/validate` | Parse SQL, enforce read-only query behavior, validate datasets and columns, and return metadata |
| `POST /query/plan` | Return custom planner artifacts for simple queries or DataFusion explain artifacts for broad SQL |
| `POST /query/execute` | Validate and execute SQL through DataFusion over registered Arrow datasets |

### Validate a query

```json
{
  "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
}
```

Example response shape:

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
  "errors": []
}
```

### Plan a query

Simple, single-table queries can use InferSQL's custom logical and physical planner. Broader SQL shapes, including joins, subqueries, derived tables, and set operations, are delegated to DataFusion explain output and returned in a structured plan response.

### Execute a query

```json
{
  "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 5"
}
```

Example response shape:

```json
{
  "sql": "...",
  "normalized_sql": "...",
  "row_count": 2,
  "columns": ["symbol", "close"],
  "rows": [
    {"symbol": "NVDA", "close": 1210.54},
    {"symbol": "MSFT", "close": 425.27}
  ],
  "logical_plan": null,
  "physical_plan": null
}
```

Use `debug=true` on supported query endpoints to include request IDs, stage timing, engine selection, error origin, and detected query features.

## Dataset registry

InferSQL uses an in-memory dataset registry as the source of truth for queryable Arrow tables and their metadata.

### Catalog endpoints

| Endpoint | Purpose |
|---|---|
| `GET /catalog/datasets` | List registered datasets, row counts, columns, types, and descriptions |
| `GET /catalog/datasets/{name}` | Return dataset detail, including samples and aliases when available |
| `POST /catalog/ingest` | Register CSV or Parquet data from a local path |
| `POST /catalog/upload` | Upload and register CSV or Parquet data |

After registration, a dataset is available immediately to `/query/execute`. Unknown tables and columns are rejected with normalized errors before execution.

## Copilot

The Copilot converts natural-language analytical requests into schema-grounded, read-only SQL candidates.

### Providers

The provider abstraction supports:

- Ollama for local-first development and evaluation
- Google Gemini when configured with an API key
- OpenAI when configured with an API key
- Fallback behavior that can use Ollama when an optional remote provider is unavailable

Relevant environment variables include:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.0
```

### Safety and validation flow

1. The intent guard blocks destructive or write-oriented requests before LLM generation.
2. The schema selector chooses relevant registered datasets from names, descriptions, columns, samples, and approved synonyms.
3. The context builder supplies schema-grounded prompt context to the configured provider.
4. The provider returns a structured SQL candidate and assumptions.
5. The query service parses and validates the candidate with SQLGlot and registry-backed schema checks.
6. Invalid candidates receive structured validation feedback and can be repaired within a bounded retry budget.
7. Only valid read-only SQL is sent to DataFusion for execution.

The intent guard blocks requests containing write operations such as `DELETE`, `UPDATE`, `INSERT`, `DROP`, `CREATE`, `ALTER`, and `TRUNCATE`. A blocked request does not invoke the LLM, validator, or executor.

### Copilot evaluation

InferSQL contains two complementary Copilot evaluation paths.

| Evaluation | Command | Purpose |
|---|---|---|
| Deterministic unit evaluation | `python -m pytest tests/test_copilot_eval.py -q` | Tests guard, retry, and orchestration behavior with controlled fake providers/services |
| Production-backed execution evaluation | `python ../scripts/run_copilot_execution_eval.py` | Uses a real configured LLM, production QueryService, SQLGlot, DataFusion, and reference-result equivalence |

The production-backed evaluator compares generated-query outputs with reference SQL outputs. It supports ordered and unordered result comparison and narrowly permits output-label variation for single aggregate results when the returned values are equivalent.

### Latest execution baseline

On September 3, 2026, local Ollama `llama3.1:8b` achieved:

| Metric | Result |
|---|---:|
| Execution-equivalent accuracy | 33/33 (100.0%) |
| Valid-query accuracy | 100.0% |
| Invalid-request rejection accuracy | 100.0% |
| First-pass valid-query accuracy | 100.0% |
| Mean attempts per case | 0.848 |
| End-to-end local LLM median latency | 39.8 s |
| End-to-end local LLM p95 latency | 47.7 s |

The 33 curated cases span 10 categories: simple selection, synonyms, aggregates, ordering, joins, subqueries, set operations, hallucination resistance, ambiguous-request clarification, and read-only safety.

The end-to-end latency figures above are dominated by local LLM generation on the benchmark machine; they are not DataFusion query-engine latency figures.

The versioned baseline artifact is stored at:

```text
backend/benchmarks/baselines/copilot_execution_eval_33_case_baseline.json
```

## Errors and debug metadata

Non-2xx query responses use a normalized error envelope:

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

- `type`: normalized error type
- `code`: uppercased error code for logs and client branching
- `message`: human-readable explanation
- `status_code`: HTTP status
- `request_id`: correlation identifier
- `debug`: optional stage, engine, error origin, and feature metadata

## Performance benchmarks

InferSQL includes an in-process benchmark harness for `/query/execute`.

```bash
python scripts/benchmark_queries.py
```

The benchmark harness:

- Starts the FastAPI application with its lifespan.
- Seeds synthetic Arrow-backed `prices_bench_*` and `fundamentals_bench_*` datasets.
- Measures filter/project/limit, grouped aggregation, order-by/limit, and join query shapes.
- Tests datasets from 1,000 to 1,000,000 rows.
- Runs 20 measured iterations per workload.
- Uses an in-process `httpx.ASGITransport` and lifespan manager.
- Writes JSON and CSV artifacts for comparison and regression analysis.

### 1M-row benchmark baseline

| Workload | Median latency | P95 latency |
|---|---:|---:|
| Filter + project + limit | 6.683 ms | 7.426 ms |
| Order by + limit | 8.906 ms | 10.283 ms |
| Grouped aggregation | 45.336 ms | 50.471 ms |
| Filtered join | 44.611 ms | 50.246 ms |

These measurements were collected over 20 iterations on Windows 10, CPython 3.11.9, AMD64, using in-process ASGI transport. They measure local API-path latency and should not be interpreted as networked, distributed, or cloud-production performance.

## Project structure

```text
backend/
  app/
    api/
      dependencies.py
      query.py
      ...
    core/
      catalog/
        registry.py
      engine/
        parser.py
        physical_planner.py
      error_handlers.py
      lifespan.py
      middleware.py
      settings.py
    schemas/
    services/
      copilot_intent_guard.py
      copilot_schema_context.py
      copilot_schema_selector.py
      copilot_service.py
      datafusion_runner.py
      query_compiler.py
      query_runner.py
      query_service.py
      llm/
  benchmarks/
    baselines/
      copilot_execution_eval_33_case_baseline.json
  tests/
    fixtures/
      copilot_eval_cases.json
      copilot_execution_eval_cases.json
frontend/
scripts/
  benchmark_queries.py
  run_copilot_execution_eval.py
```

## Development commands

Run from `backend/` unless noted otherwise.

```bash
python -m pytest -q
python -m pytest tests/test_copilot_eval.py -q
python -m pytest tests/test_copilot_intent_guard.py -q
python ../scripts/run_copilot_execution_eval.py
```

Run the performance harness from the repository root with the Python environment active:

```bash
python scripts/benchmark_queries.py
```

## Roadmap

Near-term work focuses on measurement, reliability, and reproducibility rather than unsupported feature breadth:

- Add stage-level Copilot telemetry for intent guard, schema selection, schema context, LLM generation, validation, execution, and end-to-end timing.
- Generate concise Markdown reports from evaluation JSON artifacts.
- Add baseline comparison and category-level regression checks.
- Measure repeated evaluation runs to quantify local-model variance.
- Add API concurrency benchmarks reporting throughput, p50/p95 latency, and error rate.
- Add CI checks for tests, fixture validation, and reference-SQL smoke tests.
- Evaluate retrieval-grounded schema context against the current schema-selection baseline.
- Improve Docker setup, architecture documentation, and the end-to-end demo experience.

## Author

InferSQL is developed and maintained by:

- Dong Quan Tran (Johnny)
- Owner / Collaborator
- Email: [dxt9721@mavs.uta.edu](mailto:dxt9721@mavs.uta.edu) or [dongquan.tran.johnny@gmail.com](mailto:dongquan.tran.johnny@gmail.com)
- GitHub: [dong-quan-tran](https://github.com/dong-quan-tran)
