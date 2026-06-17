# InferSQL Updated TODO List


## Current status

The backend foundation is now much stronger than when this list was first written.

Implemented or substantially improved:
- QueryService-based orchestration
- dependency injection for query services
- application factory and lifespan-oriented startup
- settings/config cleanup
- schema-aware validation for unknown datasets and unknown columns
- limit/offset pagination for `/query/execute`
- stronger tests around query contracts
- local-first copilot provider direction using Ollama
- first copilot evaluation harness
- prompt-ready schema context builder for copilot
- deterministic, question-aware schema selector for copilot
- refined copilot eval harness that tests synonyms, hallucinations, and unsupported features end-to-end

Still missing are the major SQL-dialect expansions, real dataset ingestion, richer metadata exposure, and the next layer of copilot prompt quality and synonym handling.


## Updated priority order

1. Expand the SQL engine to support the remaining MVP dialect.
2. Finish real dataset ingestion and metadata exposure.
3. Improve benchmarking and observability depth.
4. Strengthen copilot prompting, schema semantics (synonyms), validation, and evaluation.
5. Add the first thin feature-store and inference slice.


## Phase 1: Query engine completion

### 1. Add `ORDER BY` support
- Extend parser to detect and represent `ORDER BY`.
- Add logical `Sort` node.
- Add physical sort operator.
- Support ascending and descending order.
- Define/document null ordering behavior.
- Add tests for:
  - ascending sort
  - descending sort
  - sort after filter
  - sort with limit

### 2. Add aggregate support
- Extend parsing and planning for:
  - `COUNT`
  - `SUM`
  - `AVG` if feasible
- Add `GROUP BY` support.
- Add aggregate physical operators.
- Define MVP constraints clearly.
- Add tests for:
  - `COUNT(*)`
  - grouped sums
  - invalid aggregate queries
  - aggregate result consistency

### 3. Finish projection alias handling
- Ensure aliases appear correctly in summaries, plans, and execute responses.
- Preserve alias names in output columns.
- Add tests for aliased projections.

### 4. Add join groundwork
- Detect multi-table queries and join clauses.
- Define the first supported join type or explicitly reject all joins for now.
- Add stable unsupported-join errors.
- Add planner placeholders if execution is deferred.


## Phase 2: Catalog and ingestion

### 5. Build a real dataset loader
- Add CSV loading.
- Add Parquet loading.
- Register loaded tables in the registry.
- Store metadata:
  - row count
  - schema
  - source path
  - loaded timestamp
- Add fixture-based ingestion tests.

### 6. Expand catalog metadata
- Add schema introspection endpoint.
- Return dataset metadata from the registry.
- List dataset columns and types.
- **(Done)** Prepare a safe prompt-ready schema payload for copilot use:
  - Implemented `CopilotSchemaContextBuilder` that formats table/column descriptions and sample values.
  - Integrated into `CopilotService` so copilot always uses a structured schema context.


## Phase 3: Observability and performance

### 7. Deepen execution instrumentation
- Keep per-stage parse/plan/execute timing.
- Add structured logs for sql, normalized sql, request id, duration, and status.
- Add minimal OpenTelemetry spans around query lifecycle steps.
- Standardize debug metadata across endpoints.

### 8. Expand benchmarks
- Benchmark Arrow execution against a naive baseline.
- Benchmark filter/project/limit at increasing row counts.
- Save benchmark summaries and comparison artifacts.
- Add regression thresholds that fail on latency degradation.


## Phase 4: Copilot quality and safety

### 9. Improve Ollama prompt quality
- Add few-shot examples to the provider prompt.
- Add synonym mapping guidance, such as `ticker -> symbol` and `stock price -> close`.
- Move prompt examples into config/assets instead of hardcoding.
- Add tests for prompt construction behavior.

### 10. Strengthen copilot validation
- **(Partially done)** Validate generated SQL with the same parser/schema checks as the core query engine:
  - Eval harness now treats unknown datasets/columns, joins, and aggregates consistently.
- Normalize generated SQL before scoring or returning results.
- Return explicit unsupported-feature reasons for joins, aggregates, and unsupported expressions.
- Keep generation separate from execution by default.
- Ensure validation results always include:
  - `query_type`
  - `tables`
  - `columns`
  - `has_where`, `has_group_by`, `has_order_by`, `has_limit`.

### 11. Expand copilot eval coverage
- **(Done for initial slice)** Add eval cases for:
  - synonym queries (e.g. `ticker` / `price` synonyms)
  - ambiguous requests
  - hallucinated tables
  - hallucinated columns
  - unsupported joins
  - unsupported aggregates
- Track quality by category, not only overall score (to do).
- Save eval summaries for comparison over time (to do).
- Add regression thresholds for eval quality (to do).

### 12. Add schema-aware selection and context (new)

- **(Done)** Add a question-aware schema selector that:
  - scores tables using table names, descriptions, column names, column descriptions, and sample values.
  - normalizes basic plural/singular token variants to improve matching.
  - returns top-N relevant tables per question with a fallback to all tables if no scores are positive.
- **(Done)** Integrate selector with copilot schema context:
  - `CopilotService` now builds prompts using only the selected tables for each question.
- Add metrics around selected-table counts and which tables are chosen over time (to do).


## Phase 5: Feature store and inference slice

### 13. Define the smallest viable feature store slice
- Create a feature-set registry abstraction.
- Define a feature definition format.
- Materialize query results into local-only storage or cache.
- Keep the first version simple and local.

### 14. Build a minimal model registry
- Define model metadata schema.
- Register model name, version, artifact path, and input schema.
- Add read-only API endpoints.

### 15. Add a minimal inference runtime
- Load one demo model.
- Accept structured inference requests.
- Return prediction, model version, and latency metadata.
- Add end-to-end tests for feature lookup plus inference.


## Documentation

### 16. Keep architecture docs current
- Update progress logs after each milestone.
- Keep blueprint and backend docs aligned with the actual codebase.
- Track implemented vs planned vs deferred work.

### 17. Improve developer docs
- Add or refine `DEVELOPMENT.md`.
- Document local setup and test commands.
- Document the currently supported SQL subset.
- Document copilot endpoint behavior and current limits.


## Recommended immediate next sprint

1. Implement `ORDER BY` end-to-end.
2. Add few-shot prompting to the Ollama provider.
3. Add synonym-aware schema matching and prompt hints (e.g., `ticker -> symbol`, `stock price -> close`).
4. Add CSV/Parquet dataset loading.
5. Add basic category-level copilot eval summaries and regression checks.