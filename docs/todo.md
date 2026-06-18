Phase 1: Query engine completion
Add ORDER BY support

Extend parser to detect and represent ORDER BY.

Add logical Sort node.

Add physical sort operator.

Support ascending and descending order.

[~] Define/document null ordering behavior.

Effective behavior is whatever Arrow’s sort uses by default; you still need to:

Decide and document “NULLs sort last” vs “first”.

Add at least one test that explicitly hits rows with nulls to lock in behavior.

Add tests for:

ascending sort

descending sort

sort after filter

sort with limit

Add aggregate support

Extend parsing and planning for:

COUNT

SUM

AVG (MVP implementation is in place).

Add GROUP BY logical-plan support.

Add aggregate physical operators (global and grouped).

[~] Define MVP constraints clearly in docs:

The implementation enforces some constraints via validation (e.g., non-grouped columns must appear in GROUP BY or be aggregated, SELECT * with GROUP BY rejected), but this is not yet fully written up in user-facing docs.

Add tests for:

COUNT(*)

grouped sums on realistic fixtures (e.g., SUM(close) BY symbol)

invalid aggregate queries (missing GROUP BY, mixing aggregated and non-aggregated columns)

basic consistency of aggregation results (per-symbol totals, row counts, etc.)

Finish projection alias handling

Ensure SELECT close AS price is represented correctly in summaries and plans.

Logical plan includes projection metadata with {source: "close", output: "price"}.

Ensure output columns preserve alias names in execute responses.

API columns list and row dicts now use alias names.

Add tests for aliased projections:

simple alias

alias with filters

alias with grouped aggregates

Add join groundwork

Detect multi-table queries and join clauses in the parser layer (beyond rejecting them).

Decide first supported join type (probably INNER JOIN on equality) or explicitly reject all joins with structured errors.

[~] Add stable, user-friendly unsupported-join errors:

You already have some validation behavior around “joins unsupported”, but this could be sharpened and tested more explicitly.

Add planner placeholders if execution is deferred, so the logical plan can represent a Join node even if there’s no physical join yet.

Phase 2: Catalog and ingestion
Build a real dataset loader

Add CSV loading.

Add Parquet loading.

Register loaded tables in the dataset registry.

Store metadata:

row count

schema

source path

loaded timestamp

Add fixture-based ingestion tests for CSV and Parquet.

Expand catalog metadata

[~] Add schema introspection endpoint (list datasets, columns, types).

Some metadata plumbing already exists in the DatasetRegistry and is used by copilot, but there is no separate public introspection endpoint yet.

Prepare prompt-ready schema payload for copilot:

CopilotSchemaContextBuilder and metadata-rich descriptions are in place and wired into copilot.

[~] Return dataset metadata from the registry via API, not just internally for copilot.

Copilot is consuming it; public-facing catalog endpoints are still to be added.

[~] Align introspection payload format with what copilot uses.

The shape is essentially there; the missing piece is reusing or exposing it via an HTTP endpoint.

Phase 3: Observability and performance
Deepen execution instrumentation

[~] Keep per-stage parse/plan/execute timing:

Some timing exists in QueryService and logs; needs standardization and explicit tests or docs.

[~] Add structured logs for:

request id

sql and normalized sql

[~] stage timings

[~] status/outcome

Add minimal OpenTelemetry spans around query lifecycle (parse → plan → execute).

[~] Standardize debug metadata across /validate, /plan, /execute.

They share some fields; still room to make the shape fully consistent.

Expand benchmarks

Benchmark Arrow execution vs a naive row-based baseline (filter/project/limit).

Benchmark filter/project/limit at increasing row counts (1k, 10k, 100k, 1M).

Save benchmark summaries and comparison artifacts to disk.

Add regression thresholds for latency degradation.

Phase 4: Copilot quality and safety
Improve Ollama prompt quality

[~] Add few-shot examples to the provider prompt:

Prompt assets exist and are used; double-check all examples are loaded from assets and fully wired.

Add synonym mapping guidance (ticker → symbol, stock price → close, etc.) and keep it in assets/config.

[~] Add direct tests for prompt construction (shape, examples, synonyms, schema snippet).

Some tests exist around prompt assets; there’s still room for stricter prompt snapshot tests.

Strengthen copilot validation

Validate generated SQL with the same parser/schema checks as the core engine (including aggregates and joins being unsupported where appropriate).

Normalize generated SQL before scoring or returning results in the eval harness.

Return explicit unsupported-feature reasons for joins, aggregates, and other unsupported expressions (to the extent wired in current eval tests).

Keep generation separate from execution by default.

Ensure validation results always include:

query_type

tables

columns

has_where, has_group_by, has_order_by, has_limit.

Expand copilot eval coverage

[~] Add eval cases for:

synonym queries (ticker, stock price, etc.)

[~] ambiguous requests

[~] hallucinated tables

[~] hallucinated columns

unsupported joins

unsupported aggregates

Track quality by category; generate summary.

[~] Save eval summaries to disk per run and enforce regression thresholds.

Summaries exist; writing them out and enforcing thresholds in CI is still to come.

Schema-aware selection and context

Add a question-aware schema selector (implemented as CopilotSchemaSelector with tokenization, synonyms, and scoring over table/column metadata and samples).

Integrate selector with CopilotSchemaContextBuilder.

[~] Add metrics around selection behavior (tables selected per query, selection distribution, tie-in to eval outputs).

Phase 5: Feature store and inference slice
This phase is untouched so far:

Define the smallest viable feature-store slice (registry abstraction, definition format, materialization).

Build minimal model registry.

Build minimal inference runtime and end-to-end tests.

Documentation
Keep architecture docs current

[~] Add/extend a progress log.

You’ve captured progress in chat; this needs to be written into docs.

[~] Keep the architecture document in sync:

Needs explicit mention of new ORDER BY + aggregate capabilities, plus current copilot behavior.

Improve developer docs

[~] Add/refine DEVELOPMENT.md:

Basic local setup and test commands exist informally; consolidating into a doc is still outstanding.

[~] Document the currently supported SQL subset:

SELECT-only, single-table, simple WHERE, ORDER BY (single column), LIMIT, plus the new aggregate constraints.

[~] Document copilot endpoint behavior and current limitations, now updated for aggregate awareness (even if some aggregate behavior is still guarded).