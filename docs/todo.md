Legend:

- not started
- [~] in progress / partial
- done

Phase 0 – Scope & Outcomes  
Status: [~]

Remaining:
- Write `docs/scope-august.md`.
- Freeze the August claim set:
  - Broad analytical SQL over registered datasets.
  - Copilot works over the broader SQL surface.
  - Existing HTTP API shape preserved.
  - Minimal observability, benchmarks, and docs included.
- Freeze the explicit non-goals:
  - Full ANSI parity.
  - DML/DDL beyond product needs.
  - Advanced optimizer / cost-based work.
  - Enterprise auth/governance.

Phase 1 – Architecture & Contracts  
Status: done

Completed:
- Updated `docs/architecture/migration.md` direction in `development.md`:
  - `/query/execute` → DataFusion-backed.
  - `/query/plan` → custom planner for simple queries, DataFusion-backed broad planning for joins/subqueries/set ops.
  - Custom engine is documented as reference / narrow-planning code, not production execution.
- Clarified error mapping in `development.md`:
  - syntax → `InvalidQuerySyntaxError`
  - unknown dataset → `UnknownDatasetError`
  - unknown column → `UnknownColumnError`
  - ambiguous / unsupported semantics → `UnsupportedQueryError`
- Confirmed the broad-plan JSON wrapper as the current `/query/plan` contract.
- Centralized query analysis in `QueryService` and ensured all three endpoints reuse the same validation helpers.

Phase 5 – Validation Redesign  
Status: done

Completed:
- Centralized query analysis in `QueryService._analyze_query` so `/query/validate`, `/query/plan`, and `/query/execute` share:
  - normalization,
  - parsing,
  - schema/column validation.
- Documented the validation boundary in `development.md`:
  - `/query/validate` = product schema + guardrails (`SELECT`-only, registry-backed table/column checks, `SELECT *` with `GROUP BY` rejection for single-table queries).
  - `/query/execute` and broad `/query/plan` = DataFusion semantic truth; engine owns grouped/aggregate/window semantics.
- Added targeted tests to lock in the boundary:
  - `/query/validate` rejects `SELECT * FROM prices GROUP BY symbol` with a clear product error.
  - `/query/execute` surfaces the same guardrail as `UnsupportedQueryError`.
  - `/query/validate` allows queries where mixed aggregate/non-aggregate semantics are engine-owned, and `/query/execute` either runs them or returns a normalized error.

Remaining:
- None for this phase.

Phase 6 – Metadata & Schema Alignment  
Status: done

Completed:
- Documented the dataset registry as the source of truth for:
  - table names,
  - column names/types,
  - optional descriptions/sample values.
- Added a schema-alignment test module verifying consistency across:
  - registry,
  - catalog endpoints,
  - query execution column surfaces.
- Documented naming conventions for dataset registration:
  - lowercase,
  - snake_case,
  - stable API-facing dataset names,
  - lowercase snake_case column names where possible.

Phase 7 – Catalog & Ingestion  
Status: done

Completed:
- Implemented CSV ingestion via `pyarrow.csv.read_csv`.
- Implemented Parquet ingestion via `pyarrow.parquet.read_table`.
- Auto-registers loaded datasets in the registry with:
  - schema,
  - row count,
  - source path,
  - loaded timestamp.
- Wired ingestion into query execution so newly ingested datasets are queryable via `/query/execute`.
- Added catalog/API tests for:
  - CSV success,
  - Parquet success,
  - duplicate names,
  - overwrite behavior,
  - upload success for CSV and Parquet,
  - ingested datasets being queryable.
- Normalized invalid file / schema handling into API 400 responses and added tests for:
  - unsupported extensions,
  - missing file paths,
  - malformed CSV,
  - invalid Parquet.

Phase 8 – Broad SQL Capability  
Status: done

Completed:
- Added execute coverage for:
  - `LEFT JOIN`,
  - join and alias-heavy joins,
  - scalar subqueries in `SELECT`,
  - scalar subqueries in `WHERE`,
  - `HAVING` success and failure cases,
  - arithmetic and richer expressions in `SELECT` / `ORDER BY` / `WHERE`.
- Routed broad planning/execution (joins, subqueries, set ops) through DataFusion.
- Added execution coverage for a narrow window-function surface:
  - `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`,
  - `LAG(close, 1) OVER (PARTITION BY ... ORDER BY close)`,
  - `SUM(close) OVER (PARTITION BY ... ORDER BY close ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`.

Notes:
- Any window-function shapes not covered by tests are “engine-supported but not product-guaranteed” until explicitly documented.

## Phase 9 – Copilot & broad SQL evals

- [x] Replace legacy narrow copilot eval with DataFusion-backed architecture
- [x] Add deterministic EvalLLMProvider and EvalQueryService harness
- [x] Wire copilot evals to registry-backed demo dataset (`prices`)
- [x] Ensure copilot eval suite runs in CI (`test_copilot_eval.py`)
- [x] Make Gemini/OpenAI providers optional (lazy imports, optional deps)
- [x] Add live eval script using Ollama only (no paid providers required)
- [x] Expand copilot eval cases to cover aggregates and `HAVING`
- [x] Expand copilot eval cases to cover successful multi-table joins
- [x] Expand copilot eval cases to cover subqueries that succeed against a richer registry
- [x] Tune copilot repair prompts for ambiguous joins and schema mismatches

Phase 10 – Error Handling & UX  
Status: [x]

Completed:
- Normalized DataFusion errors into product exceptions (`InvalidQuerySyntaxError`, `UnknownDatasetError`, `UnknownColumnError`, `UnsupportedQueryError`, `InternalServerError`).
- Added mapping for common engine error strings (ambiguous columns, unsupported features, bad set operation shapes).
- Attached structured error envelopes (`ErrorResponse` / `ErrorDetail`) with `type`, `code`, `message`, `status_code`, `request_id` across `/query/validate`, `/query/plan`, `/query/execute`.
- Implemented optional error-level debug metadata (`debug.stage`, `debug.engine`, `debug.error_origin`) and documented it in the OpenAPI schema.
- Wired the `debug` query parameter through the request lifecycle so errors include debug metadata only when explicitly requested.
- Documented status-code and error behavior in `README.md` and `DEVELOPMENT.md`.
- Added and fixed tests covering:
  - internal engine failures and debug metadata on `/query/execute`,
  - debug metadata on `/query/validate`,
  - OpenAPI documentation for error and debug fields.

Remaining:
- None for Phase 10. Further changes to error handling or debug metadata should be considered part of future phases.

Phase 11 – Observability  
Status: done

Completed:
- Extended debug metadata to include `features` (e.g., `["join"]`, `["set_op"]`, `["window"]`, `["derived_from"]`) in validate/plan/execute debug responses.
- Added tests asserting:
  - debug metadata includes `features` as a list,
  - join queries set `"join"` in `features`,
  - window queries set `"window"` in `features`.
- Documented the current debug metadata contract in `development.md`:
  - `request_id`
  - `total_ms`
  - `stage`
  - `engine`
  - `error_origin`
  - `features`
- Standardized structured logging for query execution so `app.services.query_service` emits:
  - `stage`,
  - `total_ms`,
  - `sql_hash`,
  - `engine`,
  - `dataset`,
  - `error_code` on completion.
- Added a logging test to ensure `/query/execute` emits a structured log record with these fields.

### Phase 12 – Performance benchmark harness

- [x] Add an in-process benchmark script that exercises `/query/execute` against synthetic Arrow-backed datasets.
- [x] Seed `prices_bench_*` and `fundamentals_bench_*` tables into the in-memory registry at runtime inside the benchmark script.
- [x] Run benchmarks across 1k / 10k / 100k / 1M rows for filter, aggregate, order-by, and join query shapes.
- [x] Persist results to `benchmark_results/benchmark_summary_<RUN_ID>.json` and `.csv`, plus per-iteration CSV, and capture a Phase 12 baseline.

Phase 13 – Docs  
Status: [~]

Completed:
- Updated `development.md` to:
  - describe the hybrid DataFusion-backed architecture,
  - document the current tested SQL surface,
  - clarify validation vs engine responsibilities,
  - call out known limitations (including window and alias behavior).

Remaining:
- Rewrite `Blueprint.md` so it reflects the real current platform:
  - DataFusion-backed broad SQL backend,
  - custom validation / registry / copilot layers,
  - observability and ingestion still in progress.
- Update README with:
  - how to register datasets,
  - how to use validate/plan/execute,
  - what “broad SQL” means in practice.
- Add concrete examples:
  - join,
  - subquery,
  - `HAVING`,
  - `UNION`,
  - one copilot NL→SQL example once prompts are updated.

Phase 14 – Release Prep  
Status: [~]

Remaining:
- Add at least one end-to-end demo over 2–3 datasets:
  - ingest → validate → execute
  - copilot → execute
- Remove obsolete TODOs and stale comments.
- Verify docs match current behavior exactly.
- Tag a release candidate.
- Write short release notes:
  - new SQL capability,
  - current limitations,
  - copilot status,
  - ingestion/observability status.