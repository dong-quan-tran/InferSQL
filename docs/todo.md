Phase 1: Query engine completion
Add ORDER BY support

Extend parser to detect and represent ORDER BY.

Add logical Sort node.

Add physical sort operator.

Support ascending and descending order.

[~] Define/document null ordering behavior.

Decide and document something like “NULLs sort last” (or first) and add a test to lock it in.

Add tests for:

ascending sort

descending sort

sort after filter

sort with limit

Add aggregate support

Extend parsing and planning for:

COUNT

SUM

AVG (if feasible now)

Add GROUP BY logical-plan support.

Add aggregate physical operators (global and grouped).

Define MVP constraints clearly (e.g., one aggregate per query, no HAVING at first).

Add tests for:

COUNT(*)

grouped sums on realistic fixtures (e.g., SUM(close) BY symbol)

invalid aggregate queries (missing GROUP BY, mixing aggregated and non-aggregated columns)

consistency of aggregation results.

Finish projection alias handling

Ensure SELECT close AS price is represented correctly in summaries and plans.

Ensure output columns preserve alias names in execute responses.

Add tests for aliased projections (simple, with filters, with future aggregates).

Add join groundwork

Detect multi-table queries and join clauses in the parser layer.

Decide first supported join type (probably INNER JOIN on equality) or explicitly reject all joins for now.

Add stable, user-friendly unsupported-join errors (this is partially done at the schema-validation layer).

Add planner placeholders if execution is deferred, so the logical plan can represent a join even if the engine won’t execute it yet.

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

Add schema introspection endpoint (list datasets, columns, types).

Prepare prompt-ready schema payload for copilot:

CopilotSchemaContextBuilder is implemented and integrated.

Return dataset metadata from the registry via API, not just internally for copilot.

Align introspection payload format with what copilot uses so the same structure can be reused or trivially transformed.

Phase 3: Observability and performance
Deepen execution instrumentation

[~] Keep per-stage parse/plan/execute timing:

Timers exist in the query service, but you can standardize and make sure every endpoint populates them.

Add structured logs for:

request id

sql and normalized sql

stage timings

status/outcome

Add minimal OpenTelemetry spans around query lifecycle (parse -> plan -> execute).

Standardize debug metadata across /validate, /plan, /execute.

Expand benchmarks

Benchmark Arrow execution vs a naive row-based baseline (for at least filter/project/limit).

Benchmark filter/project/limit at increasing row counts (e.g., 1k, 10k, 100k, 1M).

Save benchmark summaries and comparison artifacts to disk so runs are comparable.

Add regression thresholds that fail CI on latency degradation beyond some percentage.

Phase 4: Copilot quality and safety
Improve Ollama prompt quality

[~] Add few-shot examples to the provider prompt (if not fully done, ensure they’re loaded from assets rather than hard-coded).

[~] Add synonym mapping guidance:

ticker -> symbol

stock price -> close

Additional domain synonyms, as needed.

Ensure prompt examples live in assets/config, not inline in code.

Add direct tests for prompt construction (shape, presence of examples, synonym hints, schema snippet).

Strengthen copilot validation

[~] Validate generated SQL with the same parser/schema checks as the core query engine:

The eval harness already exercises unknown datasets/columns, joins, and aggregates.

Normalize generated SQL before scoring or returning results (to make comparisons more robust).

Return explicit unsupported-feature reasons for:

joins (until join support exists),

aggregates (until aggregate support exists),

other unsupported expressions.

Keep generation separate from execution by default (copilot returns SQL, client chooses whether to execute).

Ensure validation results always include:

query_type

tables

columns

has_where, has_group_by, has_order_by, has_limit.

Expand copilot eval coverage

Add eval cases for:

synonym queries (ticker, stock price etc.).

ambiguous requests.

hallucinated tables.

hallucinated columns.

unsupported joins.

unsupported aggregates.

Track quality by category (you’ve got the summary structure; ensure it’s wired into your metrics).

Save eval summaries to disk as JSON artifacts per run.

Add regression thresholds for eval quality that can fail CI when accuracy drops below a given per-category floor.

Schema-aware selection and context

Add a question-aware schema selector that:

Scores tables using names, descriptions, columns, and sample values.

Normalizes basic singular/plural forms.

Returns top-N tables with safe fallback.

Integrate selector with copilot schema context builder.

Add metrics around selection behavior:

number of tables selected per query.

distribution of selected tables over time.

possibly tie selection choices into eval outputs to debug mis-grounding.

Phase 5: Feature store and inference slice
Define the smallest viable feature store slice

Create a feature-set registry abstraction (name, keys, columns, refresh policy).

Define a feature definition format (probably static YAML/JSON config for now).

Materialize query results into local-only key-value storage (in-memory dict or simple on-disk store).

Keep the first version local only; no Redis or remote infra yet.

Build a minimal model registry

Define model metadata schema (name, version, artifact path, input schema).

Implement in-memory or file-backed registry.

Add read-only API endpoints for listing models and reading metadata.

Add a minimal inference runtime

Load one demo model (e.g., a simple scikit-learn or PyTorch model).

Accept structured inference requests (features keyed by the feature registry).

Return prediction, model version, and inference latency.

Add end-to-end tests: feature lookup -> inference -> response.

Documentation
Keep architecture docs current

Add/extend a progress log (today’s entry can be the latest bullet).

Keep the architecture document in sync with what actually exists:

Document the current engine capabilities (Filter, Project, Sort, Limit).

Call out upcoming features (aggregates, joins, ingestion).

Explicitly track implemented vs planned vs deferred features.

Improve developer docs

Add or refine DEVELOPMENT.md with:

local setup,

test commands,

how to run copilot evals,

how to run benchmarks when they exist.

Document the currently supported SQL subset:

SELECT-only,

single-table,

WHERE with simple predicates,

ORDER BY (single column, ASC/DESC),

LIMIT.

Document copilot endpoint behavior and current limitations (no joins/aggregates yet, behavior on unsupported requests).

