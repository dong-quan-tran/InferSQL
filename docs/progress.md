# InferSQL Progress Log

06/12/2026:

## Overview

InferSQL is currently in the early foundation stage of the query-engine portion of the original blueprint. The current implementation centers on a FastAPI-based SQL query service backed by Apache Arrow tables, with a parser, planner, executor path, and a growing set of contract tests.

This log captures what has already been built and stabilized so the next phase of development can proceed from a clean baseline.

## Current scope

The project today is a focused SQL query API rather than the full end-state platform described in the original blueprint. The implemented surface area is concentrated around three query lifecycle endpoints:

- `/query/validate`
- `/query/plan`
- `/query/execute`

These endpoints already support a basic but real query pipeline:

1. Accept SQL input.
2. Parse SQL with SQLGlot.
3. Enforce a SELECT-only policy.
4. Summarize query structure.
5. Build logical and physical plans.
6. Execute against in-memory Apache Arrow tables.
7. Return structured JSON responses.

## What has been implemented

### 1. Dataset registry and seeded demo data

A dataset registry exists and supports:

- registering Arrow tables by dataset name
- retrieving registered datasets by normalized key
- listing registered tables
- raising a dedicated `DatasetNotFoundError` when a table is missing

A seeded demo dataset named `prices` is available when demo seeding is enabled. It currently includes a small in-memory Arrow table with at least these columns:

- `symbol`
- `close`

This provides a stable execution target for tests and endpoint development.

### 2. Query parsing and summary extraction

A `QueryParser` is implemented using SQLGlot. It currently supports:

- parsing SQL into an expression tree
- converting parse failures into a clean `ValueError("Invalid SQL syntax")`
- enforcing that only `SELECT` statements are supported
- summarizing key query metadata such as:
  - query type
  - referenced tables
  - referenced columns
  - presence of `WHERE`
  - presence of `GROUP BY`
  - presence of `ORDER BY`
  - presence of `LIMIT`

This parser is already good enough to support validation, planning metadata, and early schema checks.

### 3. Logical planning

Logical-plan generation is in place for a limited MVP SQL subset. The current logical nodes include:

- `Scan`
- `Filter`
- `Project`
- `Limit`

The parser can currently turn supported SQL into a tree that reflects the execution intent. Supported behavior includes:

- selecting specific columns
- scanning a single table
- simple `WHERE` predicates using column-vs-literal comparisons
- `LIMIT`

### 4. Predicate parsing

The current predicate support is intentionally narrow and stable. Supported operators include:

- `=`
- `!=`
- `>`
- `>=`
- `<`
- `<=`

Only simple predicates are supported right now:

- left side must be a single column
- right side must be a literal

This is enough for the demo dataset and current tests.

### 5. Physical planning and execution path

The service now compiles SQL into a physical plan and executes it through a query runner against Arrow-backed data. While the implementation is still early-stage, the end-to-end flow is real:

- SQL enters the API
- the compiler builds logical and physical plans
- the runner executes the physical plan
- results come back as rows and columns derived from an Arrow table

This means the project has already moved beyond mock responses and into a functioning execution engine MVP.

### 6. Query API endpoints

The API now exposes a clean three-step lifecycle:

#### `/query/validate`
Returns a validation report rather than executing the query. The response includes:

- original SQL
- normalized SQL
- `is_valid`
- query type
- errors array
- tables
- columns
- boolean flags for where/group/order/limit presence

#### `/query/plan`
Returns planning metadata and plan trees. The response includes:

- original SQL
- normalized SQL
- planner engine name
- ordered planning steps
- query summary
- logical plan
- physical plan

#### `/query/execute`
Runs the query and returns execution metadata plus rows. The response includes:

- original SQL
- normalized SQL
- executor engine name
- ordered execution steps
- columns
- rows
- row count
- logical plan
- physical plan
- pagination metadata

## Important improvements completed

### Structured execution metadata

Execution responses were improved so they are easier for clients and tests to consume. The execute contract now exposes structured metadata instead of only raw rows.

### Error handler hardening

Validation error handling was fixed so FastAPI validation errors are converted into JSON-safe responses. This resolved a crash where embedded Python `ValueError` objects inside validation context were not JSON serializable.

### Pagination support for execution

`/query/execute` now supports API-level pagination using `limit` and `offset`. The response includes:

- `limit`
- `offset`
- `has_more`

Arrow result slicing is used after execution to page the returned rows safely.

### Schema-aware column validation

A major milestone was added: schema-aware validation against the registered Arrow dataset.

The service now checks referenced columns before planning or executing a query. For single-table queries, it compares referenced column names against `table.column_names` from the registered dataset. This allows the API to fail fast with clear messages like:

- `Unknown column 'nope' on dataset 'prices'`

This validation now applies across:

- `/query/plan`
- `/query/execute`
- `/query/validate` via in-band validation errors

### Query validation upgraded

`/query/validate` now behaves like a true diagnostics endpoint:

- it still returns HTTP 200 for well-formed requests
- it sets `is_valid` to `False` when the SQL is invalid semantically or structurally
- it reports schema errors through the `errors` list rather than crashing or prematurely executing

## Test coverage completed so far

The test suite now covers a meaningful amount of project behavior.

### Existing areas under test

- config loading
- dataset registry behavior
- OpenAPI exposure
- query validation behavior
- query planning behavior
- query execution behavior
- response schema compatibility
- smoke tests

### Specific test scenarios now covered

- blank SQL rejection
- non-SELECT rejection
- expected response shape for plan and execute endpoints
- query whitespace normalization
- filter-node inclusion in plans
- successful row execution against seeded demo data
- unknown-column rejection in plan and execute
- unknown-column reporting in validate
- pagination-related execute behavior

At this stage, the project has a strong API-contract safety net for the currently supported SQL subset.

## Current technical boundaries

The current implementation is intentionally narrow. The following limitations still exist and are acceptable for the present stage:

- only `SELECT` queries are supported
- only single-table queries are supported
- only simple literal `WHERE` predicates are supported
- no joins yet
- no aggregate execution yet
- no sort execution yet
- no cost estimation yet
- no result caching yet
- execution is in-memory and demo-oriented
- feature store, inference runtime, observability dashboards, and LLM copilot are not built yet

## Current architecture snapshot

The implemented backend is best described as:

- FastAPI control surface
- SQLGlot-based parser
- custom query parser/planner layer
- Arrow-backed dataset registry
- query compiler
- physical query runner
- structured error handlers
- pytest contract coverage

This is a legitimate MVP core for the future vectorized query engine described in the original blueprint.

## What is now true of the project

At this point, InferSQL can already be described as:

- a functioning SQL query API
- a working parser → plan → execute pipeline
- a small in-memory Arrow query engine prototype
- a schema-aware and test-driven backend foundation

That is a meaningful milestone. The project is no longer just a design document; it is a running system with real endpoint behavior, real planning artifacts, and a real execution path.


Progress log – 2026‑06‑16

Copilot eval harness and validator
Fixed the eval harness so that it properly distinguishes between referenced and projected columns.

Validation now reports output columns based on the SELECT list, not every column that appears in WHERE.

Execution stubs in the eval tests were updated to return column lists that match the projection.

Tightened the fake validator logic used in tests:

ticker and price are now treated as unknown columns, which drives the retry path.

Aggregates like COUNT, SUM, AVG are mapped to “unsupported expression” in the eval harness.

Multi-table / join cases and hallucinated tables/columns now hit explicit unsupported/unknown errors instead of falling through.

Result: the copilot eval suite now accurately exercises:

simple selects, filters, and limits,

synonym repair (ticker -> symbol, price -> close),

hallucinated-table and hallucinated-column behavior,

unsupported-aggregate and unsupported-join behavior.

Copilot service behavior
Refined CopilotService.query to:

Run validate–retry loops with clear logging of validation errors per attempt.

Ensure execution only occurs once a candidate passes validation.

Fixed several subtle contract mismatches between the service and the eval harness:

Validation results now consistently carry has_where, has_group_by, has_order_by, has_limit flags.

Execution result shape (columns and row counts) now aligns with what tests expect.

Prompt-ready schema context
Extracted schema-context formatting from CopilotService into a dedicated schema context builder:

CopilotSchemaContextBuilder reads from DatasetRegistry.describe_table and produces a concise, LLM-friendly description:

Table name and optional table description.

Column names and types.

Optional column descriptions.

Optional sample values (up to a configurable limit).

The builder is unit-tested to ensure it includes descriptions and examples when requested and can omit samples when disabled.

CopilotService now just asks the builder for a schema context instead of hand-rolling strings, making the prompt payload:

Easier to test,

Easier to evolve (e.g., trimming samples or changing wording),

Clearly separated from service orchestration logic.

Question‑aware schema selection
Added a deterministic schema selector in front of the schema context builder:

CopilotSchemaSelector scores each table against the user question using token overlap across:

Table name,

Table description,

Column names,

Column descriptions,

Sample values (with a lower weight).

Implemented lightweight token normalization (singular/plural handling like prices → price, symbols → symbol) for more robust matches.

Weighted scoring to prioritize:

Column name hits > table name hits > description hits > sample-value hits.

Integrated selector into CopilotService:

_build_schema_context(question) now:

Uses the selector to choose the top relevant tables for the question.

Asks the schema context builder to render only those tables.

All existing copilot tests were adjusted by fixing the call site to pass question into _build_schema_context.

Added tests for:

Preferring prices for “stock price” questions.

Preferring fundamentals for “market cap” questions.

Falling back to “all tables” when no useful overlap is found.

Progress log: 06/17/2026

1. ORDER BY end-to-end
Planning

Extended the parser to:

Recognize ORDER BY clauses.

Extract sort keys as { column, direction }, with ASC as default and DESC explicitly captured.

Updated the logical planner to:

Insert a Sort logical node between Project and Limit when an ORDER BY is present.

Preserve the order of sort keys so multi-column sorts are supported later if needed.

Updated the physical planner to:

Map logical Sort -> physical Sort operator.

Keep Limit as the final node, so the pipeline is: Scan -> Filter -> Project -> Sort -> Limit.

Execution

Implemented a SortOperator using Arrow:

Uses pyarrow.compute.sort_indices with mapped orders: "ASC" -> "ascending", "DESC" -> "descending".

Applies sort to the entire table and then reuses existing pagination logic (Limit + API-level limit/offset).

Updated QueryExecutor to:

Recognize the Sort physical node.

Execute Sort after Project (and Filter) but before Limit.

Tests

Planning tests:

Added coverage for:

ORDER BY close (ascending default).

ORDER BY close DESC.

WHERE ... ORDER BY ... LIMIT ensures the tree order is Scan -> Filter -> Project -> Sort -> Limit.

Execution tests:

Verified:

Ascending sort returns rows where close values are sorted increasing.

Descending sort returns rows sorted decreasing.

Sort-after-filter respects both filter predicate and sort order.

Confirmed both logical and physical plans show Sort between Project and Limit.

Net result: ORDER BY is now fully wired and observable in /query/plan and /query/execute.

2. Logging robustness + tests
Logging behavior

Hardened non-JSON logging:

The plain-text formatter previously assumed every record had stage, dataset, and error_code fields, causing formatting errors when they were missing.

Added a safe formatter that:

Ensures stage, dataset, error_code, and request_id exist on every record.

Falls back to "-" when a field is not present.

JSON logging was already robust; we left it as-is and just ensured both code paths share the same request-id filter.

Logging tests

Added a small logging smoke test module that:

Configures JSON logging, logs once, asserts the output is valid JSON and contains message, request_id, logger, and level.

Configures plain-text logging, logs once without extra fields, and asserts:

No errors are emitted.

The log line includes the logger name, the message, and the request id.

Net result: logging no longer crashes under either JSON or plain-text configuration, and this behavior is now guarded by tests.


Progress log: 06/18/2026

Aggregation and GROUP BY support

Extended the parser to recognize aggregate functions (COUNT, SUM, AVG) and GROUP BY expressions, building an Aggregate logical node with group_keys and aggregates metadata.

Implemented aggregate execution with Arrow-backed operators, including grouped aggregation (e.g., SUM(close) BY symbol) and global aggregates like COUNT(*).

Added validation to reject invalid aggregate queries (e.g., mixing aggregated and non-aggregated columns without proper GROUP BY, or unsupported SELECT * with GROUP BY) and wired this through QueryService and /query/validate.

Added tests for grouped sums on realistic demo data (prices) and for negative aggregate cases to lock in the MVP constraints.

Projection alias handling

Updated QueryParser.build_logical_plan so Project nodes carry a richer details structure, including both columns and a projections list of {source, output} pairs.

Refactored the Project executor to:

Select real source columns from the input Arrow table.

Rename them to output/alias names in the result schema (so SELECT close AS price yields a column named price).

Updated the query plan endpoint and parser unit tests to assert the new Project.details shape while preserving expectations for columns.

Added execute-level tests to ensure:

Aliases appear in the API columns list.

Row dictionaries use alias keys (e.g., price not close).

Aliases behave correctly with filters and grouped aggregates.

ORDER BY integration confidence

Confirmed ORDER BY planning still produces Sort logical nodes with the expected key metadata and sits in the correct position in the logical plan (Scan → Filter → Project → Sort → Limit).

Verified that ORDER BY + LIMIT scenarios are covered by tests and remain green after the projection/aggregation refactors.

All tests are green at the end of this work.

Progress log: 2026-06-19
Tightened the catalog and registry layer to return richer, metadata-aware dataset descriptions and aligned unit tests for the updated shape (including samples).

Implemented and wired a Copilot schema context builder that now includes column descriptions, aliases, and representative example values, and fixed its integration with prompt-assets.

Added HTTP catalog endpoints and schemas to expose dataset metadata publicly, then exercised them with API tests.

Cleaned up LLM/copilot schema-context behavior so all copilot and eval tests pass again (including the eval harness and selection tests).

Got the entire backend test suite back to fully green (117 tests) after all catalog/copilot refactors.


Progress log: 06/20/2026

Switched query execution from the custom physical executor path to a new DataFusion-backed execution path for /query/execute, while keeping the API output stable as row_count, columns, and rows.

Added and wired a new DataFusionRunner that builds a SessionContext, registers in-memory Arrow tables from DatasetRegistry, executes SQL, collects result batches, and converts them back into the existing execution response model.

Fixed DataFusion table registration by passing record batches in partitioned form (list[list[RecordBatch]]), which is required by register_record_batches.

Kept the current planner and most of the existing validation surface in place so the migration is incremental rather than a rewrite.

Relaxed validation to allow multi-table queries and joins, replacing blanket “JOIN not supported” failures with dataset-aware and column-aware validation errors.

Added join execution coverage with smoke tests for INNER JOIN and LEFT JOIN, plus validation tests for allowed joins, unknown aliased columns, and ambiguous unqualified columns. DataFusion documents support for inner and left joins directly.

Updated older tests that assumed joins must fail so they now reflect the new behavior: joins are permitted, but unknown datasets such as sectors still fail as schema errors.

Verified that the full backend test suite is green after the migration slice, which means the DataFusion-backed execute path is stable enough to build on next.

Progress log: 06/21/2026

Engine and planning
Ensured /query/execute consistently routes through DataFusion for all supported SQL, with the custom engine restricted to reference planning for simple single-table queries.

Implemented a DataFusion-backed /query/plan path for broad SQL:

Simple single-table queries still use the legacy logical/physical planner.

Joins, subqueries, and set operations now use a DataFusion EXPLAIN-based planner.

Plan responses for broad queries are mapped into the existing logical_plan / physical_plan JSON shape while preserving engine metadata.

Validation and SQL surface
Relaxed validation so it no longer rejects joins or subqueries-in-FROM by default.

Confirmed that:

Multi-table joins and subqueries can execute and plan successfully.

Schema checks (dataset and column existence, ambiguous unqualified columns) still run at the product level.

Aligned /query/plan behavior with /query/execute for broad SQL, using lightweight table-existence validation before delegating to DataFusion.

Error normalization
Centralized mapping of DataFusion parse/planning/execution errors into the existing product error types:

InvalidQuerySyntaxError

UnknownDatasetError

UnknownColumnError

UnsupportedQueryError

Added coverage for:

Union column-count mismatches.

Invalid/unsupported subquery shapes.

Unknown datasets, unknown columns, and ambiguous column references.

Ensured that both /query/plan and /query/execute now return stable, tested error shapes for broad SQL failures.

Observability (minimal)
Introduced timing-based debug metadata (using time.perf_counter) for:

/query/validate

/query/plan

/query/execute

Standardized a debug object shape with:

request_id

total_ms

stage (“validate”, “plan”, “execute”)

engine (“infersql-planner” or “datafusion”)

error_origin (placeholder for future tagging)

Added tests to assert the presence and shape of debug metadata on debug=true responses.

Test suite
Brought the full backend test suite to green, including:

Broad-join planning tests that assert DataFusion usage for complex queries.

Subquery-in-FROM planning and execution tests.

New tests asserting normalized error responses and debug metadata.


# Progress – 2026-06-22

## Backend & engine integration

- Centralized query analysis in `QueryService._analyze_query`, so `/query/validate`, `/query/plan`, and `/query/execute` share normalization, parsing, and schema validation.
- Adjusted `/query/plan` routing so simple single-table queries use the custom planner and broad SQL (joins/subqueries/set ops) delegates planning to DataFusion.
- Fixed schema validation for subqueries in `FROM` by:
  - treating derived-table aliases (`FROM (...) AS q`) as their own scope,
  - avoiding false `UnknownColumnError` when referencing `q.symbol` in the outer query.
- Ensured `QueryService.execute` uses the shared analysis path without regressing tests.

## DataFusion runner

- Refactored `DataFusionRunner` to use a shared `_collect_table` execution helper reused by:
  - `run_table`,
  - `explain`,
  - `run`.
- Restored the original record-batch registration shape with DataFusion (`ctx.register_record_batches(table_name, [table.to_batches()])`) to keep all broad SQL tests green.[web:405][web:337]

## Debug metadata & observability

- Extended debug payloads for validate/plan/execute to include a `features` array derived from parsed SQL, indicating presence of:
  - joins (`"join"`),
  - set operations (`"set_op"`),
  - window functions (`"window"`),
  - top-level derived `FROM` (`"derived_from"`).

## Documentation

- Updated `development.md` to:
  - explicitly describe the hybrid architecture and DataFusion’s role,
  - document the current tested SQL surface and boundaries,
  - clarify validation vs engine responsibilities,
  - call out known limitations (e.g., non-SELECT statements, window functions as “not yet” until fully documented).
- Updated `todo.md`:
  - marked Phase 1 (Architecture & Contracts) as done,
  - captured today’s work under Phases 8, 10, 11, and 13,
  - kept remaining items focused on window-function decision, copilot, observability, and docs.

## Test status

- Full backend test suite passes:
  - `tests/test_query_execute.py`
  - `tests/test_query_plan.py`
  - `tests/test_query_validate.py`
  - and remaining unit + smoke tests.

### 2026-06-23 – Phase 9 copilot/eval work

- Fixed copilot eval harness to robustly extract the original question from prompts and fail clearly when the marker is missing.
- Reworked `EvalQueryService` to model current product behavior instead of the old narrow-SQL world, including:
  - explicit handling of unknown datasets (`trades`, `fundamentals`),
  - unknown column checks for `ticker`, `price`, `sector`,
  - basic support for joins and grouped aggregates in the fake validator and executor.
- Refactored `test_copilot_eval.py` to:
  - share a single `_assert_eval_case` helper between the parametrized test and the summary test,
  - add an eval-suite summary with category-level pass-rate thresholds (including a new `aggregate` category).
- Made Gemini and OpenAI providers truly optional:
  - moved SDK imports into provider `__init__` with clear error messages if the packages are missing,
  - hardened JSON parsing and error reporting for all providers (Gemini, OpenAI, Ollama),
  - updated the LLM factory to lazy-import optional providers and always provide an Ollama fallback.
- Added a live copilot eval runner script (Ollama-only) that:
  - loads `copilot_eval_cases.json`,
  - runs `CopilotService` with a simple Arrow-backed `prices` registry,
  - evaluates each case using the same assertions as the unit tests,
  - prints a JSON summary plus failure details,
  - enforces configurable overall and per-category pass-rate thresholds.
- Extended the copilot eval suite to cover aggregate + `HAVING` behavior under a dedicated `aggregate` category.
- Confirmed all tests are green (`python -m pytest`) after the Phase 9 changes.


# Progress Log — 2026-06-24

## Summary

Wrapped up Phase 10 for InferSQL backend work: error handling, debug metadata, copilot eval stability, OpenAPI/schema alignment, and docs were all completed.

## Completed

- Fixed the copilot eval harness so all `test_copilot_eval.py` cases pass.
- Hardened `QueryService` error mapping from DataFusion into product exceptions.
- Added structured internal engine metadata using:
  - `engine="datafusion"`
  - `error_origin="engine_execution"`
- Normalized error responses across query endpoints with a consistent `error` envelope.
- Wired `debug=true` through the query API so error responses include optional debug metadata.
- Updated OpenAPI-facing schemas so `ErrorDetail.debug` is documented and tested.
- Fixed execute/validate failure-path tests around internal engine errors and debug payloads.
- Updated `README.md`, `DEVELOPMENT.md`, and `todo.md` to reflect the final Phase 10 behavior.
- Marked Phase 10 as complete.

## Files touched

- `app/api/query.py`
- `app/core/error_handlers.py`
- `app/core/exceptions.py`
- `app/services/query_service.py`
- `app/schemas/query.py`
- `tests/test_copilot_eval.py`
- `tests/test_query_execute.py`
- `tests/test_query_validate.py`
- `tests/test_openapi.py`
- `README.md`
- `DEVELOPMENT.md`
- `todo.md`

## Outcome

- All tests are green.
- Query error handling is now consistent across service, API, schema, and docs.
- Debug metadata is implemented, documented, and covered by tests.
- Phase 10 is fully wrapped up and should not need to be revisited unless the error contract changes in a future phase.