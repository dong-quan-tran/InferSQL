# InferSQL Blueprint

## Current positioning

InferSQL is being built as a backend platform for analytical SQL, dataset-aware validation, and guarded SQL copilot workflows.

The current platform is centered on a **DataFusion-backed query engine** with product-owned layers around it:

- a FastAPI HTTP API,
- an in-memory dataset registry,
- SQLGlot-based parsing and query summarization,
- product-level validation and guardrails,
- normalized error handling,
- a small copilot layer for NL-to-SQL generation and evaluation.

This blueprint reflects the system that exists today, not the original narrower custom-engine-first design.

## What InferSQL is today

Today, InferSQL is primarily a query platform over registered Arrow-backed datasets.

It currently provides:

1. A query API with validate, plan, and execute endpoints.
2. A registry-backed metadata layer that controls what datasets are queryable.
3. A hybrid planning model:
   - legacy custom planning for some simple single-table queries,
   - DataFusion-backed planning for broader SQL shapes.
4. DataFusion-backed execution for the tested SQL surface.
5. A guarded copilot flow that generates SQL against the registered schema context.

It does **not** yet represent a complete feature store, inference runtime, or production observability stack. Those remain later platform layers.

## Platform definition

InferSQL is evolving toward a unified AI data plane, but the current practical platform is:

- an analytical SQL backend over registered datasets,
- a schema-aware validation and error-normalization layer,
- a copilot layer that uses the same registry and query service contracts,
- a foundation for future ingestion, observability, and feature-serving work.

The architectural rule is simple:

- the query engine is the spine,
- registry metadata is the source of truth,
- copilot and future platform features must build on those shared contracts.

## Current implemented architecture

### Query API layer

The backend currently exposes these core endpoints:

- `POST /query/validate`
- `POST /query/plan`
- `POST /query/execute`

It also exposes dataset catalog and ingestion endpoints around the registry:

- `GET /catalog/datasets`
- `GET /catalog/datasets/{name}`
- `POST /catalog/ingest`
- `POST /catalog/upload`

These APIs operate over the same registered datasets and share the same application state.

### Runtime flow

The current request lifecycle is:

1. FastAPI receives the request.
2. Lifespan startup initializes shared application services on `app.state`.
3. SQLGlot parses SQL for product-owned validation and query shape inspection.
4. The dataset registry is consulted for dataset existence and schema metadata.
5. Product validation applies:
   - `SELECT`-only enforcement,
   - dataset existence checks,
   - column existence checks,
   - ambiguity checks,
   - limited guardrails.
6. Planning and execution proceed through one of two paths:
   - legacy custom planner for some simple `/query/plan` cases,
   - DataFusion-backed planning and execution for broad SQL.
7. Responses are normalized into stable API contracts with optional debug metadata.

### Core services

The live platform currently depends on the following application-level components:

- `DatasetRegistry`
- `QueryParser`
- `PhysicalPlanner`
- `QueryCompiler`
- `QueryRunner`
- `QueryService`
- `CopilotService`
- `LLMProvider`

These are initialized during FastAPI lifespan startup and attached to `app.state` for dependency injection.

## Architecture overview

### Current architecture

```text
Client
  │
  ▼
FastAPI API Layer
  │
  ├── Query endpoints
  │   ├── /query/validate
  │   ├── /query/plan
  │   └── /query/execute
  │
  ├── Catalog endpoints
  │   ├── /catalog/datasets
  │   ├── /catalog/datasets/{name}
  │   ├── /catalog/ingest
  │   └── /catalog/upload
  │
  ▼
Application services
  │
  ├── DatasetRegistry
  ├── QueryParser (SQLGlot)
  ├── QueryService
  ├── QueryCompiler
  ├── QueryRunner
  ├── PhysicalPlanner
  ├── CopilotService
  └── LLMProvider
  │
  ▼
Execution / planning layer
  │
  ├── Legacy custom planner path for narrow simple planning cases
  └── DataFusion-backed planning and execution for broad SQL
  │
  ▼
Arrow-backed registered datasets
```

### Near-term architecture target

```text
Client
  │
  ▼
FastAPI API Layer
  │
  ├── Query API
  ├── Catalog / ingestion API
  ├── Copilot API
  └── Debug / schema inspection API
  │
  ▼
Shared platform services
  │
  ├── Registry + schema metadata
  ├── Parser + validator
  ├── DataFusion-backed planner / executor
  ├── Copilot schema context + prompts
  ├── Benchmark harness
  └── Logging / debug metadata / tracing hooks
  │
  ▼
Arrow / CSV / Parquet datasets
```

### Longer-term platform target

```text
┌─────────────────────────────────────────────────────┐
│                    CONTROL PLANE                    │
│   Config · Model Registry · Deployment Workflows    │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                      DATA PLANE                     │
│                                                     │
│   Query Engine → Feature Services → Inference       │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                    COPILOT LAYER                    │
│     NL→SQL · Query Explainability · Ops Assistant   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                 OBSERVABILITY LAYER                 │
│      Logs · Metrics · Traces · Benchmarking         │
└─────────────────────────────────────────────────────┘
```

This remains the long-term direction, but the active engineering focus is still the query engine core plus the first copilot slice.

## SQL engine model

InferSQL is no longer a narrow custom execution engine.

The real model today is:

- DataFusion is the primary execution engine.
- DataFusion is also the planning source for broader SQL in `/query/plan`.
- the custom engine remains as a limited planning/reference path for some simple cases.
- product validation remains outside the engine and is intentionally narrower than full SQL semantics.

This separation matters:

- `/query/validate` is a precheck and policy layer,
- `/query/plan` is hybrid,
- `/query/execute` is the source of truth for tested query behavior.

## SQL surface and product boundaries

InferSQL supports a broad but explicit analytical SQL subset over registered datasets.

At a high level, the tested surface includes:

- `SELECT` queries only,
- single-table and multi-table queries,
- joins,
- subqueries,
- set operations such as `UNION` and `UNION ALL`,
- grouped aggregates and `HAVING`,
- `ORDER BY`,
- `LIMIT`,
- tested expressions in projection and filters.

The exact contract should be treated as the one documented in `development.md`.

Two important product boundaries apply:

1. InferSQL does **not** claim full ANSI SQL support.
2. InferSQL only claims support for behavior that is tested and documented.

## Validation and engine responsibilities

The platform intentionally splits responsibility between product validation and engine semantics.

### Product-owned responsibilities

The validation layer is responsible for:

- enforcing `SELECT`-only behavior,
- checking whether referenced datasets exist,
- checking whether referenced columns exist,
- detecting some ambiguous multi-table column references,
- applying a limited set of product guardrails,
- shaping stable API validation responses.

### Engine-owned responsibilities

DataFusion is responsible for:

- semantic SQL correctness,
- grouped aggregate legality,
- join semantics,
- subquery semantics,
- set-operation behavior,
- execution correctness,
- broad planning behavior.

This means a query can pass `/query/validate` and still fail `/query/execute` if the engine rejects its semantics.

## Dataset model

The dataset registry is the source of truth for queryable datasets.

A dataset becomes queryable only after it is registered in the registry. The registry owns:

- dataset names,
- Arrow tables,
- column names,
- column types,
- optional dataset descriptions,
- optional column descriptions,
- source metadata such as `source_path`,
- load metadata such as `loaded_at`.

Current implications:

- if a dataset is not registered, it is not queryable,
- if a column is not in the registry schema, it is unknown to product validation,
- catalog APIs serialize registry-backed metadata,
- ingestion APIs ultimately register Arrow tables into the registry.

The current registry is in-memory within the running process. That is sufficient for local development and tests, but it is not yet a persistence layer.

## Ingestion model

InferSQL now includes a basic ingestion path for local datasets.

Current ingestion scope:

- CSV ingestion,
- Parquet ingestion,
- registration into the in-memory dataset registry,
- immediate availability to query execution after registration.

This is an important step toward the target platform, but ingestion is still early-stage. It is not yet a full dataset management system with persistence, versioning, lineage, or storage abstraction.

## Copilot model

InferSQL includes a small copilot layer designed around the live schema and query contracts.

The current copilot flow is:

1. build schema context from the dataset registry,
2. prompt an `LLMProvider` for a structured SQL candidate,
3. validate that candidate through the query service,
4. optionally execute it through the same query path,
5. return structured candidate, validation, and execution output.

The important architectural decision is that copilot does **not** bypass the query platform. It depends on the same registry, validation, and execution contracts as other product surfaces.

This keeps copilot grounded in the real platform rather than inventing a separate SQL capability model.

## Observability status

Observability exists today in a limited but useful form.

Current implemented pieces include:

- request-scoped logging,
- structured error normalization,
- debug metadata on validate, plan, and execute endpoints,
- timing information via `debug=true`,
- a local benchmark harness for `/query/execute`.

Observability is still incomplete.

Still in progress or still future-facing:

- deeper OpenTelemetry coverage,
- production metrics and dashboards,
- richer tracing across parse / validate / plan / execute stages,
- persistent benchmark tracking,
- operational alerts and SLOs.

## Benchmarking status

A local benchmark harness now exists for the query engine.

Current benchmark scope:

- in-process benchmarking through the ASGI app,
- synthetic Arrow-backed benchmark datasets,
- multiple row sizes,
- representative query shapes including filter, aggregate, order-by, and join,
- JSON and CSV benchmark artifacts.

This benchmark layer is intended to provide a repeatable local baseline for `/query/execute`, not a final production performance program.

## Repository blueprint

The repository today is organized around the current backend platform:

```text
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── query.py
│   │   └── ...
│   ├── core/
│   │   ├── catalog/
│   │   │   └── registry.py
│   │   ├── engine/
│   │   │   ├── parser.py
│   │   │   ├── physical_planner.py
│   │   │   └── ...
│   │   ├── error_handlers.py
│   │   ├── lifespan.py
│   │   ├── middleware.py
│   │   └── settings.py
│   ├── schemas/
│   └── services/
│       ├── copilot_service.py
│       ├── query_compiler.py
│       ├── query_runner.py
│       ├── query_service.py
│       └── llm/
├── scripts/
├── tests/
└── ...
```

The structure should continue to evolve around shared services rather than separate feature silos.

## Roadmap framing

### Milestone A: Query platform stabilization

Target:

- stable validate / plan / execute behavior,
- explicit tested SQL surface,
- registry-backed ingestion and metadata,
- repeatable benchmark coverage,
- consistent debug and error behavior.

### Milestone B: Copilot and schema services

Target:

- stronger copilot grounding,
- better schema/context endpoints,
- broader evaluated NL-to-SQL coverage,
- clearer multi-table and ambiguity handling.

### Milestone C: Observability and platform extensions

Target:

- better tracing and metrics,
- persistent operational visibility,
- first feature-serving and inference-adjacent slices built on the query engine,
- gradual expansion toward a fuller AI data plane.

## Engineering principles

1. **Keep the supported SQL surface explicit**  
   Only document and claim support for what is tested.

2. **Preserve one source of truth for schema**  
   The dataset registry must remain the source of truth for dataset and column metadata.

3. **Treat DataFusion as the primary engine**  
   Do not design new execution behavior around the legacy narrow path.

4. **Keep product validation separate from engine semantics**  
   Product guardrails should stay understandable and limited.

5. **Build new layers on shared contracts**  
   Copilot, ingestion, observability, and future services should reuse the same registry and query-service contracts.

6. **Prefer vertical slices over speculative architecture**  
   A working, tested slice is more valuable than a larger but unverified roadmap claim.

## Near-term definition of success

In the near term, InferSQL should be able to truthfully claim:

- broad analytical SQL over registered datasets through a DataFusion-backed backend,
- a stable registry and ingestion model for local analytical datasets,
- product-owned validation and normalized API behavior,
- a guarded copilot flow grounded in the real schema and query contracts,
- enough benchmark and debug infrastructure to support iterative engine work.