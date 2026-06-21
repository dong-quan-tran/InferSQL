# InferSQL Blueprint (DataFusion-backed)

## Current positioning

InferSQL is still being built as a unified AI data plane, but the implementation is now centered around a DataFusion-backed analytical engine wrapped in a product-specific API, validation, and copilot layer.

The backend exposes a stable HTTP contract (`/query/validate`, `/query/plan`, `/query/execute`) backed by:

- Apache Arrow datasets.
- Apache DataFusion as the primary execution engine.
- SQLGlot parsing and summarization.
- Schema-aware, product-level validation.
- Structured error normalization and minimal observability.

This blueprint keeps the original ambition while aligning the roadmap with the system that exists today.

## Product definition (current focus)

InferSQL is a backend platform that will eventually unify four capabilities:

1. A vectorized analytical query engine.
2. A low-latency feature serving and model inference layer.
3. A safe LLM copilot for SQL and platform operations.
4. A production-style observability stack.

Today, the focus is on (1) with a thin slice of (3) for SQL copilot behavior. Work on (2) and (4) will only proceed once the query-engine core is stable.

## Current implemented foundation

### Query API

The backend exposes three core endpoints:

- `POST /query/validate`
- `POST /query/plan`
- `POST /query/execute`

These share a consistent validation and error model, and they all operate over the same registered datasets.

### Query lifecycle

The request flow currently supports:

1. SQL ingestion through FastAPI.
2. SQL parsing and summarization through SQLGlot.
3. Product-specific validation (statement type, datasets, columns, guardrails).
4. Either:
   - Custom logical/physical planning for simple single-table queries, or
   - DataFusion-backed planning for broader SQL.
5. Execution against Arrow-backed data via DataFusion.
6. Structured JSON responses including normalized errors and optional debug metadata.

### Current SQL surface (high-level)

Broadly, InferSQL now supports:

- Analytical `SELECT` queries over registered datasets.
- Single-table and multi-table queries.
- Joins.
- Subqueries (including subquery-in-FROM).
- Set operations such as `UNION` / `UNION ALL`, with shape validation.
- `ORDER BY` and `LIMIT`.
- Basic grouped aggregates (with stricter rules where enforced by the product).
- A subset of expressions in `SELECT`, `WHERE`, and `ORDER BY`.

The exact tested surface is documented in `development.md` and is intentionally narrower than full ANSI SQL. DataFusion provides a much larger SQL surface; InferSQL exposes the subset that is tested and behaves well in the current product [web:26][web:243][web:16].

## Updated architecture

### Phase 1 architecture: implemented core

```text
Client
  │
  ▼
FastAPI Query API
  │
  ├── /query/validate
  ├── /query/plan
  └── /query/execute
  │
  ▼
QueryService
  │
  ├── DatasetRegistry
  ├── QueryParser (SQLGlot)
  ├── QueryCompiler (narrow logical/physical plans)
  ├── DataFusionRunner (broad execution/planning)
  └── QueryRunner (legacy, narrow)
  │
  ▼
Arrow-backed datasets registered in DatasetRegistry
```

Key facts:

- `/query/execute` routes through DataFusion for execution.
- `/query/plan` uses:
  - the custom planner for simple queries, and
  - DataFusion EXPLAIN for broad queries (joins, subqueries, set operations).
- The registry remains the source of truth for table and column metadata.

### Phase 2 architecture: near-term target

```text
Client
  │
  ▼
FastAPI API Layer
  │
  ├── Query API
  ├── Dataset API
  └── Debug/Schema API
  │
  ▼
QueryService
  │
  ├── Catalog + DatasetLoader (CSV/Parquet)
  ├── Parser + Validator (SQLGlot-based)
  ├── Logical Planner (custom for simple queries)
  ├── DataFusion Planner/EXPLAIN for broad queries
  ├── DataFusion-backed Execution
  ├── Copilot Schema Context + Prompts
  └── Benchmarks + Instrumentation
  │
  ▼
Arrow / Parquet / CSV datasets
```

The near-term focus is:

- CSV/Parquet ingestion wired into the registry and DataFusion.
- Schema alignment between registry, copilot, and engine.
- Documented and observable query lifecycle.

### Phase 3 architecture: expanded platform target

```text
┌─────────────────────────────────────────────────────┐
│                   CONTROL PLANE                     │
│  Model Registry · Deployment Manager · Config       │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                      DATA PLANE                     │
│                                                     │
│  Query Engine → Feature Store → Inference Runtime   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                    COPILOT LAYER                    │
│  NL→SQL · Plan Explainer · Ops Assistant            │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                 OBSERVABILITY STACK                 │
│  OTel · Prometheus · Grafana · Logs · Traces        │
└─────────────────────────────────────────────────────┘
```

This remains the long-term direction; current work is focused on stabilizing the `Query Engine` and the initial `Copilot` slice.

## Revised repository blueprint

The repository structure is still:

```text
backend/
├── app/
│   ├── api/
│   │   └── query.py
│   ├── core/
│   │   ├── catalog/
│   │   │   └── registry.py
│   │   ├── engine/
│   │   │   └── parser.py
│   │   ├── error_handlers.py
│   │   ├── middleware.py
│   │   ├── lifespan.py
│   │   └── settings.py
│   ├── schemas/
│   │   └── query.py
│   └── services/
│       ├── query_service.py
│       ├── query_compiler.py
│       └── query_runner.py
├── tests/
├── docs/
└── pyproject.toml
```

Future expansion still leaves room for:

```text
backend/
├── app/
│   ├── api/
│   │   ├── query.py
│   │   ├── datasets.py
│   │   ├── models.py
│   │   ├── deployments.py
│   │   └── features.py
│   ├── core/
│   │   ├── catalog/
│   │   ├── engine/
│   │   │   ├── parser.py
│   │   │   ├── planner.py
│   │   │   ├── operators/
│   │   │   └── optimizer.py
│   │   ├── feature_store/
│   │   ├── inference/
│   │   └── observability/
│   ├── copilot/
│   └── services/
├── frontend/
├── configs/
├── docs/
└── tests/
```

## Updated milestone plan (condensed)

### Milestone A: Broad SQL Core (current)

Target:

- DataFusion-backed execution for a defined analytical SQL subset.
- `/query/validate`, `/query/plan`, `/query/execute` stable and consistent.
- CSV/Parquet ingestion and registry integration.
- Minimal observability (debug metadata, basic logging, simple benchmarks).

### Milestone B: Copilot & Schema Services

Target:

- Copilot capable of generating valid SQL for single- and multi-table questions.
- Schema endpoints for inspection and copilot context.
- Better ambiguous-join handling and error messaging.

### Milestone C: Observability & Feature-Serving Slice

Target:

- OTEL spans around key flows.
- Baseline dashboards and metrics.
- First feature-store/inference integrations using the query engine as the spine.

## Current query API contract (updated)

### `POST /query/validate`

Purpose: product-level pre-check.

- Accepts SQL plus optional options.
- Returns:
  - `is_valid` flag.
  - query summary (tables, columns, shape flags).
  - product-level validation errors, if any.

### `POST /query/plan`

Purpose: planning artifacts.

- For simple queries:
  - Returns custom logical/physical plans.
- For broad queries:
  - Wraps DataFusion EXPLAIN output into a `logical_plan` / `physical_plan` JSON structure.
- Always returns:
  - `sql`, `normalized_sql`.
  - `engine`.
  - `steps`.
  - `logical_plan`, `physical_plan`.
  - Optional `debug` metadata.

### `POST /query/execute`

Purpose: execute and return results.

- Validates query (schema + guardrails).
- Executes via DataFusion.
- Returns:
  - `row_count`, `columns`, `rows`.
  - Optional logical/physical plan (where available).
  - Optional `debug` metadata (timings, engine, stage).

## Engineering principles (unchanged but sharpened)

1. **Keep the SQL subset explicit**  
   Only claim support for the SQL features that are tested and well-behaved in the product.

2. **Prefer correctness over breadth**  
   Each new feature must ship with tests, error handling, and docs.

3. **Reuse validation logic**  
   Validation logic should be shared across validate/plan/execute so behavior stays consistent.

4. **Use the query engine as the spine**  
   Feature serving, copilot, and inference should build on the query engine, not bypass it.

5. **Layer the roadmap**  
   Maintain a functioning system at all times; add new capabilities in vertical slices.

## Near-term definition of success

In the near term, InferSQL should be able to truthfully claim:

- Broad analytical SQL (joins, subqueries, unions, grouped aggregates) over registered datasets, backed by DataFusion [web:26][web:243].
- Stable dataset registration and schema introspection.
- Structured error handling and minimal observability (debug metadata, logs).
- A backend foundation strong enough to power a guarded SQL copilot and future feature store.