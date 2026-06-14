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