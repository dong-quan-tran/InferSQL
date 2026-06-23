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
Status: [~]

Remaining:
- Decide whether to keep or remove the remaining single-table GROUP BY product-level checks.
- Document the validation boundary clearly:
  - `/query/validate` = product schema + guardrails.
  - `/query/execute` and broad `/query/plan` = DataFusion semantic truth.
- Add a few targeted tests for:
  - ambiguous alias cases,
  - edge-case grouped queries,
  - odd syntax/product-policy queries.

Phase 6 – Metadata & Schema Alignment  
Status: not started

Remaining:
- Make the registry the clearly documented source of truth for:
  - table names,
  - column names/types,
  - optional descriptions/sample values.
- Add one schema-alignment test module verifying consistency across:
  - registry,
  - catalog endpoints,
  - copilot schema context,
  - DataFusion registration.
- Document naming conventions for dataset registration.

Phase 7 – Catalog & Ingestion  
Status: not started

Remaining:
- Finish CSV ingestion.
- Finish Parquet ingestion.
- Auto-register loaded datasets in the registry with:
  - schema,
  - row count,
  - source path,
  - loaded timestamp.
- Wire ingestion into DataFusion registration.
- Add tests for:
  - CSV success,
  - Parquet success,
  - duplicate names,
  - invalid file / schema handling.

Phase 8 – Broad SQL Capability  
Status: [~]

Completed:
- Added execute coverage for:
  - `LEFT JOIN`,
  - join and alias-heavy joins,
  - scalar subqueries in `SELECT`,
  - scalar subqueries in `WHERE`,
  - `HAVING` success and failure cases,
  - arithmetic and richer expressions in `SELECT` / `ORDER BY` / `WHERE`.
- Routed broad planning/execution (joins, subqueries, set ops) through DataFusion.

Remaining:
- Decide whether to include window functions in August:
  - if yes, finalize `ROW_NUMBER`, `LAG`, and simple `SUM OVER` behavior and document them as supported;
  - if no, document them explicitly as not yet supported.
- Keep the SQL support list tied to tested behavior, not aspirational claims.

Phase 9 – Copilot Migration  
Status: not started

Remaining:
- Update prompts so they no longer assume narrow SQL only.
- Add few-shot examples for:
  - joins,
  - `HAVING`,
  - subqueries,
  - `UNION` / `UNION ALL`.
- Update repair prompts for:
  - ambiguous columns,
  - hallucinated join keys,
  - unknown columns.
- Add eval cases for:
  - multi-table joins,
  - ambiguous joins,
  - grouped + `HAVING`,
  - nested subqueries.
- Track category-level copilot quality metrics.

Phase 10 – Error Handling & UX  
Status: [~]

Completed:
- Normalized DataFusion errors into product exceptions (`InvalidQuerySyntaxError`, `UnknownDatasetError`, `UnknownColumnError`, `UnsupportedQueryError`).
- Added mapping for common engine error strings (ambiguous columns, unsupported features, bad set operation shapes).

Remaining:
- Decide whether to expose `error_origin` in debug metadata only or document it as a stable field.
- Decide whether to add a dedicated `DataFusionExecutionError` for internal engine failures.
- Add a few final failure-path tests:
  - unsupported window features if windows are attempted,
  - any remaining engine-planning edge cases worth normalizing.
- Document status-code behavior in one place.

Phase 11 – Observability  
Status: [~]

Completed:
- Extended debug metadata to include `features` (e.g., `["join"]`, `["set_op"]`, `["window"]`, `["derived_from"]`) in validate/plan/execute debug responses.

Remaining:
- Document the current debug metadata contract:
  - `request_id`
  - `total_ms`
  - `stage`
  - `engine`
  - `error_origin`
  - `features`
- Improve structured logging so it consistently captures:
  - normalized SQL or hash,
  - engine used,
  - outcome/error code,
  - stage timings.
- Optionally add minimal OTEL spans around:
  - validate,
  - plan,
  - execute,
  - copilot generation/repair later.

Phase 12 – Benchmarks  
Status: not started

Remaining:
- Build the benchmark script for:
  - filter/project/limit,
  - aggregate/group by,
  - order by + limit,
  - joins.
- Run it over:
  - 1k,
  - 10k,
  - 100k,
  - 1M rows.
- Save CSV/JSON summaries to disk.
- Check in a baseline file and short interpretation notes.

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