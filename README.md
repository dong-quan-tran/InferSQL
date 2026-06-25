# InferSQL

InferSQL is a Python-based analytical SQL engine with a schema-aware LLM copilot. It focuses on:

- A small but solid **Arrow-backed query engine** (parse → logical plan → physical plan → execution).
- A **FastAPI** backend for SQL validation, planning, and execution.
- A guarded **natural-language-to-SQL copilot** with pluggable LLM providers (Ollama, Gemini, OpenAI).
- Early **observability hooks** suitable for turning into a full tracing/logging story.

The long-term vision is closer to internal infra at a quant/AI-native company than a typical CRUD app: a compact analytical engine, a catalog and feature-store layer, an inference slice, and a copilot sitting safely on top.

---

## Current capabilities (engine and copilot)

### Query engine

The current engine is columnar and Arrow-based:

- **Data model:** Apache Arrow tables held in a `DatasetRegistry`.
- **SQL pipeline:** `QueryParser` → logical plan → physical plan → `QueryRunner`/executor.
- **Supported logical/physical operators (MVP):**
  - `Scan` – read a named dataset from the in-memory registry.
  - `Filter` – simple `WHERE` predicates on a single table.
  - `Project` – select and rename columns, with alias preservation.
  - `Sort` – `ORDER BY` on a single table, with ASC/DESC support and nulls sorting last.
  - `Aggregate` – basic aggregates over Arrow:
    - `COUNT`, including `COUNT(*)`.
    - `SUM`.
    - `AVG`.
    - `GROUP BY` over one or more grouping keys, with strict MVP semantics.
  - `Limit` – `LIMIT n`.

The engine is intentionally narrow right now:

- **SELECT-only**, single-table queries.
- `WHERE` with simple comparisons (e.g., `column > 100`).
- `ORDER BY` on one or more projected/queryable columns.
- Global aggregates (no `GROUP BY`) when the select list is aggregates only.
- `GROUP BY` + aggregates with a small, well-defined surface and validation:
  - Non-aggregated columns must appear in `GROUP BY`.
  - `SELECT *` with `GROUP BY` is rejected.
  - Only plain columns + simple aggregates in grouped select lists.
- **No joins yet** – joins are explicitly treated as unsupported, with structured errors.

The logical plan encodes explicit node types and metadata:

- `Scan` – `{ "table": "prices" }`
- `Filter` – `{ "predicate": { "column": "close", "operator": ">", "value": 100, "sql": "close > 100" } }`
- `Project` – carries both:
  - `columns`: the **output** column names in order.
  - `projections`: `{ "source": ..., "output": ... }` pairs, so `SELECT close AS price` is represented as `{ "source": "close", "output": "price" }`.
- `Aggregate` – `group_keys` plus `aggregates` entries like `{ "func": "SUM", "column": "close", "alias": "total_close" }`.
- `Sort` – `keys` as `{ "column": "close", "direction": "ASC" | "DESC" }`.
- `Limit` – `{ "count": 10 }`.

Execution uses PyArrow tables and operators rather than row loops.

For a more detailed description of the supported SQL subset and current semantics (including ORDER BY and GROUP BY rules), see `DEVELOPMENT.md`.

### Copilot

InferSQL includes a schema-aware, validation-first copilot:

- **Provider abstraction:**
  - Pluggable LLM provider interface with:
    - Ollama backend (local-first).
    - Gemini backend via `google-genai`.
    - OpenAI backend via the official `openai` client.
  - A provider factory that supports `ollama`, `gemini`, `openai`, and `auto` mode (auto chooses based on configured keys).
  - A **fallback provider** that wraps a primary provider with an Ollama fallback on errors.

- **Prompting and schema awareness:**
  - A shared prompt builder that:
    - Builds a system prompt with strict JSON-only, SQL-only instructions.
    - Injects synonym guidance (e.g., `ticker → symbol`, `stock price → close`).
    - Provides few-shot examples loaded from assets (not hard-coded in the provider).
    - Attaches a JSON schema describing the expected `CopilotSqlCandidate` shape.
  - A `CopilotSchemaSelector` that:
    - Scores tables based on names, descriptions, columns, and sample values.
    - Normalizes simple singular/plural forms.
    - Uses synonym rules to improve matching.
    - Returns the top-N relevant tables (with safe fallbacks).
  - A `CopilotSchemaContextBuilder` that:
    - Renders schema context text including table/column descriptions, aliases, and sample values.
    - Uses the same metadata that powers the query engine/catalog.

- **Validation and repair loop:**
  - `CopilotService`:
    - Takes a natural-language question.
    - Uses the schema selector and context builder.
    - Calls the chosen LLM provider to produce a `CopilotSqlCandidate`.
    - Validates the candidate via the **same** `QueryService` path used by the core engine:
      - Parse, plan, schema checks, supported features (including aggregate and join restrictions).
    - If invalid, constructs a **repair prompt** including:
      - Original question.
      - Schema context.
      - Previous SQL and validation errors.
      - Requests a corrected SELECT-only SQL candidate (no joins yet, aggregates guarded).
    - Repeats up to a configured max retries and returns a detailed `CopilotQueryResponse` including:
      - Final candidate.
      - Validation results (tables, columns, `has_where`, `has_group_by`, `has_order_by`, `has_limit`).
      - Optional execution result if execution was requested and validation passed.
      - Retry history and whether a repair was needed.

- **Eval harness:**
  - A copilot evaluation harness with:
    - Cases for synonyms, hallucinated tables/columns, and unsupported joins/aggregates.
    - Per-category metrics and a summary structure.
  - Structured so regression thresholds and artifact persistence can be added later.

---

## API surface

The backend is a FastAPI application that exposes:

- `/query/validate` – parse and validate SQL, return metadata:
  - `query_type`, `tables`, `columns`, `has_where`, `has_group_by`, `has_order_by`, `has_limit`.
- `/query/plan` – return:
  - Original and normalized SQL.
  - High-level steps (parse, validate, plan, build physical plan).
  - A JSON representation of the logical and physical plans.
- `/query/execute` – validate, plan, execute, and return:
  - Result rows and column names.
  - Basic execution metadata (e.g., dataset name, row counts).
- Copilot endpoints (names/paths may evolve) for:
  - Natural language → SQL candidate generation.
  - Validation and optional execution.
  - Eval harness runs and summaries (primarily for internal use).

All services are constructed in a FastAPI lifespan function that:

- Loads settings (including LLM provider config).
- Configures logging.
- Builds:
  - `QueryService` (registry, parser, planner, runner).
  - LLM provider via the provider factory.
  - `CopilotService` using those components.

### Error responses

All query endpoints (`/query/validate`, `/query/plan`, `/query/execute`) return a normalized error envelope on non-2xx responses:

```json
{
  "error": {
    "type": "InvalidQuerySyntaxError",
    "code": "INVALIDQUERYSYNTAXERROR",
    "message": "Invalid SQL syntax",
    "status_code": 400,
    "request_id": "b9fc0a0e-...",
    "debug": {
      "stage": "error",
      "engine": "datafusion",
      "error_origin": "engine_execution"
    }
  }
}
```

- `type` – exception class name (e.g., `EmptyQueryError`, `UnknownDatasetError`, `InternalServerError`).
- `code` – uppercased version of `type`, suitable for logs and client-side branching.
- `message` – human-readable description of the error.
- `status_code` – HTTP status (400, 404, 500).
- `request_id` – correlation ID; also present in structured logs.

The optional `debug` object is only present when debug mode is enabled (see below):

- `stage` – currently `"error"` when populated by the global error handler.
- `engine` – the query engine that raised the error (e.g., `"datafusion"` for internal execution failures), or `null` when not applicable.
- `error_origin` – coarse origin classification (e.g., `"engine_execution"` for internal execution engine failures).

The error envelope is modeled by `ErrorResponse`/`ErrorDetail` in `app/schemas/query.py` and produced by the custom handlers in `app/core/error_handlers.py`.

### Debug flag

The query endpoints accept an optional `debug` query parameter:

- `debug=false` (default): responses omit internal engine details and only return the normalized error envelope.
- `debug=true`: the backend:
  - Sets `request.state.debug` so downstream code can emit richer diagnostics.
  - Attaches a `debug` object to error responses with `stage`, `engine`, and `error_origin`.

The debug flag is intended for local development and internal tooling, not for untrusted clients in production.

---

## Configuration

Configuration is handled via a Pydantic `Settings` model:

- **Core app:**
  - `app_name`, `app_version`, `environment`.
  - `seed_demo_data` (e.g., a seeded `prices` table).
- **Logging:**
  - `log_json`, `log_level`.
- **Observability:**
  - `service_name`.
  - Flags for console span exporters, etc.
- **LLM setup:**
  - `llm_provider` – `"ollama"`, `"gemini"`, `"openai"`, or `"auto"`.
  - `llm_temperature`.
  - Ollama: `ollama_base_url`, `ollama_model`.
  - Gemini: `gemini_api_key`, `gemini_model`.
  - OpenAI: `openai_api_key`, `openai_model`.

Settings are loaded once via a helper and reused across the app.

---

## Observability (current state and direction)

Right now:

- Middleware is wired in at the ASGI/FastAPI layer in an OTEL-friendly way.
- An observability module builds an OpenTelemetry `Resource` using `service_name` and configuration.
- Logging includes:
  - `request_id` (for correlation).
  - Stage tags like `"validate"`, `"plan"`, `"execute"` in `QueryService`.

Planned next steps:

- Standardize per-stage timings (parse/plan/execute) across `/validate`, `/plan`, `/execute`.
- Add minimal spans around the query lifecycle.
- Layer in structured logs with normalized SQL and status/outcome.
- Add benchmark scripts and regression thresholds around latency.

---

## Repository structure (backend)

This README is focused on the backend engine + copilot. The relevant folder is:

```text
backend/
  └── app/
      ├── api/          # FastAPI endpoints (query, copilot, etc.)
      ├── core/
      │   ├── engine/   # Parser, logical/physical planner, executor
      │   ├── observability/
      │   └── settings.py
      ├── schemas/      # Pydantic models (plan nodes, copilot models, API responses)
      └── services/
          ├── query_service.py
          ├── query_runner.py
          ├── copilot_service.py
          └── llm/      # Provider interfaces and implementations
tests/
  # Engine, service, copilot, and provider tests
```

The broader “feature store / inference runtime / control plane” shown in the original vision is not fully implemented yet; those remain part of the roadmap.

---

## What’s implemented vs planned

### Implemented

- Arrow-backed analytical query engine:
  - Single-table SELECT queries with `WHERE`, `ORDER BY`, `GROUP BY`, aggregates, and `LIMIT`.
  - Logical and physical planning with explicit node types.
  - Execution over Arrow tables via a small set of operators.
- In-memory dataset registry with demo tables (via `seed_demo_data`, including `prices` and `prices_nulls` for null-ordering tests).
- Schema-aware copilot:
  - Pluggable LLM provider layer (Ollama, Gemini, OpenAI, auto-selection, and fallback).
  - Schema selection and context building.
  - Strict JSON-only `CopilotSqlCandidate` contract with validation and repair.
  - Eval harness for copilot quality.
- FastAPI HTTP API for:
  - SQL validation, planning, and execution.
  - Copilot query and eval (names and contract may evolve).
- Basic observability hooks at the middleware and service layers.
- A reasonably comprehensive test suite covering:
  - Parser and planner behavior.
  - Query service, runner, and aggregate/ORDER BY semantics.
  - Copilot flows, provider factory, and fallback behavior.
  - Copilot eval harness behavior.

### Planned / not yet built

- **Joins:**
  - Multi-table parsing, logical `Join` nodes, and a physical join operator (likely starting with inner equi-join).
  - Clear “joins unsupported” errors and/or planner placeholders until execution is ready.

- **Catalog and ingestion:**
  - CSV and Parquet ingestion endpoints.
  - Registry-backed metadata (schema, row count, source path, last loaded).
  - Public schema introspection endpoints aligned with copilot schema context.

- **Observability & performance:**
  - Standardized parse/plan/execute timing in all endpoints.
  - OTEL span instrumentation around the query lifecycle.
  - Benchmark scripts and regression gates in CI.

- **Feature store and inference slice:**
  - Feature-set registry, small local feature store, and a minimal model/inference slice.
  - End-to-end “feature lookup → model prediction” path reusing the query engine.

- **Docs and developer UX:**
  - Up-to-date architecture diagrams focused on the current engine + copilot.
  - Additional docs for running copilot evals and (later) benchmarks.

---

## Running the backend locally

From the `backend/` directory:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Run the API (dev)
uvicorn app.main:app --reload
```

By default, the app:

- Loads settings from environment variables / `.env`.
- Seeds demo datasets if `seed_demo_data=true`.
- Exposes `/query` and copilot endpoints under the FastAPI app.

Once running, you can:

- Hit `/docs` for interactive OpenAPI docs.
- Use `/query/validate`, `/query/plan`, `/query/execute` for SQL.
- Use copilot endpoints to experiment with NL → SQL workflows (assuming an LLM provider is configured).

---

## Status

InferSQL is actively evolving. The current focus is:

1. **Engine completion:** solidifying ORDER BY semantics, aggregates, and GROUP BY behavior with clear validation.
2. **Catalog and ingestion:** CSV/Parquet loaders and a metadata-rich catalog.
3. **Copilot safety and accuracy:** better evals, more guardrails, and richer schema awareness.
4. **Observability and benchmarks:** turning the existing hooks into a real instrumentation story.

The feature-store and inference runtime pieces remain on the roadmap and will build on top of this core engine and copilot foundation.