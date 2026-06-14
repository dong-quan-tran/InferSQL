# InferSQL Detailed TODO List

## Goal of the next phase

The next phase should keep the project tightly aligned with the original InferSQL vision while staying realistic about what has actually been built so far. The immediate priority is to deepen the query engine MVP into a stronger analytical backend before branching into feature serving, inference, observability, and the copilot layer.

## Priority order

The recommended build order is:

1. Expand the SQL engine to support the intended MVP query dialect.
2. Improve correctness, contracts, and test depth.
3. Add performance and observability hooks around query execution.
4. Introduce dataset loading and richer catalog metadata.
5. Build the first thin vertical slice of feature serving and inference.
6. Add the first safe copilot entry point.

## Phase 1: Query engine completion

### 1. Add `ORDER BY` support

#### Why this matters
The original blueprint includes `ORDER BY` in the MVP SQL dialect. It is also one of the most visible missing features for a query engine.

#### Tasks
- Extend the parser to detect and represent `ORDER BY` clauses in the logical plan.
- Add a logical `Sort` node.
- Add a physical `Sort` node/operator.
- Support ascending and descending sort directions.
- Define deterministic behavior for null ordering or explicitly document the current choice.
- Add tests for:
  - single-column ascending sort
  - single-column descending sort
  - sorting after filter
  - sorting with limit

### 2. Add aggregate support

#### Why this matters
Aggregation is central to analytical SQL and is explicitly part of the original project blueprint.

#### Tasks
- Extend parsing and logical planning for:
  - `SUM`
  - `COUNT`
  - `AVG` if feasible after SUM/COUNT
- Add `GROUP BY` logical-plan support.
- Add aggregate physical operators.
- Decide on MVP constraints, for example:
  - single aggregate function at first
  - grouped aggregation before global aggregation
- Add tests for:
  - `COUNT(*)`
  - grouped `SUM(close)` by `symbol` on a richer fixture
  - invalid aggregate queries
  - consistency of aggregation results

### 3. Add projection alias support cleanup

#### Why this matters
Aliases become important as soon as aggregate expressions and more complex projections appear.

#### Tasks
- Ensure `SELECT close AS price` is represented correctly in summaries and plans.
- Ensure output columns preserve alias names.
- Add tests for aliased projections in both plan and execute responses.

### 4. Add join planning groundwork

#### Why this matters
The original blueprint expects hash joins later. Full join execution can wait, but groundwork should begin once single-table analytical support is solid.

#### Tasks
- Extend parsing support to detect multi-table queries and join clauses.
- Decide the first supported join type, likely `INNER JOIN` on equi-join predicates.
- Add explicit errors for unsupported join patterns.
- Add planner-level placeholders if full execution is deferred.

## Phase 2: Correctness and API maturity

### 5. Strengthen schema validation

#### Tasks
- Add unknown-table diagnostics to `/query/validate`, `/query/plan`, and `/query/execute`.
- Improve error messages for qualified columns like `prices.close`.
- Add clearer messages for unsupported expressions.
- Validate that projected columns, predicate columns, and future group/order columns all exist before execution.
- Add tests for:
  - unknown dataset
  - qualified unknown column
  - unsupported multi-table references
  - unsupported predicate structure

### 6. Add request and response model cleanup

#### Tasks
- Review all endpoint response models for exact alignment with actual payloads.
- Separate validate/plan/execute schemas cleanly if any shared model is over-constraining endpoints.
- Standardize `engine` and `steps` metadata across endpoints.
- Add typed request models if any endpoints still accept raw dict payloads.

### 7. Add execution safeguards

#### Tasks
- Enforce a server-side max result size.
- Decide how SQL `LIMIT` interacts with API `limit` and `offset`.
- Reject pathological requests with clear messages.
- Add timeout boundaries around expensive execution paths.

## Phase 3: Better catalog and dataset ingestion

### 8. Build a real dataset loader

#### Why this matters
The current seeded Arrow table is useful, but the blueprint is built around datasets loaded from files and eventually richer data sources.

#### Tasks
- Add CSV loader support.
- Add Parquet loader support.
- Register loaded tables in the dataset registry.
- Store metadata such as:
  - row count
  - schema
  - source path
  - last loaded timestamp
- Add tests for loading datasets from fixture files.

### 9. Expand catalog metadata

#### Tasks
- Add a schema introspection endpoint.
- Return dataset metadata from the registry, not only raw tables.
- Support listing column names and types for each dataset.
- Prepare a safe schema payload that can later be injected into the copilot prompt.

## Phase 4: Query engine observability and benchmarks

### 10. Add execution instrumentation

#### Why this matters
Observability is a major part of the original blueprint, and query execution is the easiest place to start.

#### Tasks
- Add timing around parse, plan, and execute stages.
- Include per-stage timing in debug responses.
- Add structured logs for request id, sql, normalized sql, duration, and status.
- Add minimal OpenTelemetry spans around query lifecycle steps.

### 11. Add benchmarks

#### Tasks
- Benchmark current Arrow-backed execution against a naive row-based baseline.
- Benchmark filter/project/limit queries at increasing row counts.
- Publish baseline numbers in docs.
- Add a reproducible benchmark script.

## Phase 5: First feature-store and inference slice

### 12. Define the smallest viable feature store slice

#### Tasks
- Create a feature-set registry abstraction.
- Define a format for feature definitions.
- Build a simple materialization path from query results into a key-value store or in-memory cache.
- Start with local-only backing storage before Redis if needed for speed of delivery.

### 13. Build a minimal model registry

#### Tasks
- Define model metadata schema.
- Register model name, version, artifact path, and input schema.
- Add a read-only API to list models.
- Delay advanced deployment modes until the registry contract is stable.

### 14. Add a minimal inference runtime

#### Tasks
- Support loading one demo model.
- Accept a structured inference request.
- Return prediction, model version, and latency metadata.
- Add end-to-end tests for feature lookup plus inference.

## Phase 6: Copilot foundation

### 15. Add a guarded natural-language to SQL prototype

#### Why this matters
The original blueprint includes an LLM copilot, but it should sit on top of a stable schema-aware query API.

#### Tasks
- Build a prompt schema using dataset metadata from the catalog.
- Restrict generation to the currently supported SQL subset.
- Validate generated SQL with the same parser and schema checks already used by the core service.
- Return generated SQL without auto-executing at first.
- Add prompt-injection rejection tests.

## Documentation tasks

### 16. Keep architecture docs current

#### Tasks
- Maintain a progress log after every major milestone.
- Keep the blueprint synchronized with the actual codebase.
- Record what is implemented vs planned vs deferred.
- Add a concise backend architecture document focused on the current system, not only the aspirational future one.

### 17. Improve developer onboarding docs

#### Tasks
- Add `DEVELOPMENT.md` with local setup instructions.
- Document test commands and known environment requirements.
- Document current supported SQL subset.
- Document current endpoint contracts with example payloads and responses.

## Recommended immediate next sprint

The best next sprint is:

1. Implement `ORDER BY` end-to-end.
2. Add unknown-table validation tests.
3. Add CSV/Parquet dataset loading.
4. Add per-stage query timing in debug responses.
5. Benchmark current filter/project/limit performance.

This sequence keeps the project aligned with the original blueprint while continuing to build on the strongest part of the current codebase: the query engine core.