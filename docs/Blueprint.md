# InferSQL Updated Blueprint

## Current positioning

InferSQL is being built as a unified AI data plane, but the actual implementation today is concentrated in the backend query-engine layer. The project currently has a working FastAPI SQL service backed by Apache Arrow data, SQLGlot parsing, structured planning, schema-aware validation, and endpoint-level execution.

This updated blueprint keeps the ambition of the original vision while aligning the roadmap to the system that already exists.

## Product definition

InferSQL is a backend platform that will eventually unify four capabilities:

1. A vectorized analytical query engine.
2. A low-latency feature serving and model inference layer.
3. A safe LLM copilot for SQL and platform operations.
4. A production-style observability stack.

At the current stage, only the first capability is materially implemented, and even that is at MVP depth. The project should therefore be developed in layers, beginning with a strong query-engine core and only then expanding outward.

## Current implemented foundation

The following capabilities already exist in the codebase:

### Query API

The backend exposes three core endpoints:

- `POST /query/validate`
- `POST /query/plan`
- `POST /query/execute`

### Query lifecycle

The request flow currently supports:

1. SQL ingestion through FastAPI.
2. SQL parsing through SQLGlot.
3. SELECT-only enforcement.
4. Query metadata summarization.
5. Logical-plan generation.
6. Physical-plan generation.
7. Execution against Arrow-backed in-memory data.
8. Structured JSON responses.

### Current SQL subset

Supported today:

- `SELECT`
- `FROM` with a single table
- `WHERE` with simple column-vs-literal predicates
- `LIMIT`
- projection of selected columns
- query normalization and query summaries
- schema-aware column validation

Not yet supported today:

- `ORDER BY` execution
- `GROUP BY` execution
- aggregate functions
- joins
- optimizer rules like projection pruning and predicate pushdown as explicit planner phases
- cost estimation
- result caching

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
  ├── QueryParser (SQLGlot-backed)
  ├── QueryCompiler
  └── QueryRunner
  │
  ▼
Apache Arrow tables
```

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
  ├── Catalog + DatasetLoader
  ├── Parser
  ├── Logical Planner
  ├── Physical Planner
  ├── Vectorized Operators
  └── Benchmarks + Instrumentation
  │
  ▼
Arrow / Parquet / CSV datasets
```

### Phase 3 architecture: expanded platform target

```text
┌─────────────────────────────────────────────────────┐
│                    CONTROL PLANE                    │
│  Model Registry · Deployment Manager · Config       │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                     DATA PLANE                      │
│                                                     │
│  Query Engine → Feature Store → Inference Runtime   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                   COPILOT LAYER                     │
│  NL→SQL · Plan Explainer · Ops Assistant            │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                OBSERVABILITY STACK                  │
│  OTel · Prometheus · Grafana · Logs · Traces        │
└─────────────────────────────────────────────────────┘
```

## Revised repository blueprint

The repository structure should reflect what exists now while leaving room for the original long-term vision.

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

### Planned expansion path

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

## Updated milestone plan

## Milestone 1: Solidify the current query engine MVP

### Delivered
- dataset registry
- seeded demo Arrow dataset
- SQL parser integration
- SELECT-only validation
- query summaries
- logical and physical plans
- execution endpoint
- structured error handling
- pagination on execute
- schema-aware column validation
- meaningful pytest coverage

### Remaining in this milestone
- `ORDER BY`
- aggregate functions
- `GROUP BY`
- richer plan metadata
- unknown-table diagnostics
- dataset loading from CSV and Parquet
- execution timing and instrumentation

## Milestone 2: Add vectorized analytical depth

### Target capabilities
- explicit vectorized operators for scan/filter/project/sort/aggregate
- optimizer passes such as predicate pushdown and projection pruning
- benchmark suite against naive row-oriented execution
- richer schema catalog and dataset metadata

### Acceptance criteria
- can run representative analytical queries over larger fixture datasets
- publishes benchmark results
- exposes debug timings per query stage

## Milestone 3: Introduce dataset and schema services

### Target capabilities
- dataset ingestion endpoints
- schema inspection endpoints
- multiple registered datasets
- richer validation context for queries and future copilot use

### Acceptance criteria
- datasets can be loaded and registered without code edits
- schema metadata is queryable through the API

## Milestone 4: Build the first feature-serving and inference slice

### Target capabilities
- feature registry
- online feature lookup
- model registry
- one working inference endpoint

### Acceptance criteria
- one demo model can be registered and invoked using fetched features

## Milestone 5: Add observability

### Target capabilities
- OpenTelemetry spans around query, feature, and inference workflows
- Prometheus metrics
- structured request logs
- basic Grafana dashboards

### Acceptance criteria
- end-to-end tracing exists for query execution
- latency metrics are visible without code inspection

## Milestone 6: Add the copilot layer

### Target capabilities
- guarded NL→SQL generation for the supported SQL subset
- plan explanation endpoint
- schema-bounded prompts
- audit logging for copilot actions

### Acceptance criteria
- can generate safe SQL for supported questions
- can explain query plans in plain language

## Current contract for the query API

### `POST /query/validate`
Purpose: return a validation report without running the query.

Expected behavior:
- HTTP 200 for valid request bodies
- `is_valid` indicates semantic and structural validity
- `errors` contains human-readable diagnostics
- includes tables, columns, and query-shape flags

### `POST /query/plan`
Purpose: return planning artifacts for a supported query.

Expected behavior:
- schema-aware validation happens before planning
- returns normalized SQL, engine, ordered steps, summary, logical plan, and physical plan
- returns client-safe errors for unsupported or invalid references

### `POST /query/execute`
Purpose: run the query and return paginated results.

Expected behavior:
- schema-aware validation before execution
- execution metadata included in response
- `limit`, `offset`, and `has_more` included
- rows serialized from Arrow result slices

## Engineering principles for the current stage

### 1. Keep the SQL subset explicit
Do not imply support for features that do not exist. The documentation and API behavior should match the current engine exactly.

### 2. Prefer correctness over breadth
Each added SQL feature should come with tests, stable error messages, and response-contract updates.

### 3. Reuse validation logic
Schema and query validation should live in shared helpers so validate, plan, and execute stay consistent.

### 4. Use the query engine as the spine of the whole platform
Feature materialization, future copilot generation, and inference enrichment should all build on the query layer rather than bypass it.

### 5. Keep the roadmap layered
The original blueprint is still valid as a long-term destination, but the implementation should move in vertical slices that preserve a functioning system at every step.

## What success looks like next

The next strong version of InferSQL should be able to truthfully claim:

- support for a practical analytical SQL subset including sort and aggregation
- stable dataset loading and schema introspection
- measurable query performance characteristics
- observable execution stages
- a backend foundation strong enough to power feature serving and a guarded copilot

That is the right bridge between the current MVP and the full original platform vision.