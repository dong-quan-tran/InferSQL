Legend:

not started

[~] partially done

done

Phase 0: Freeze scope
Define the August finish line clearly:

broad analytical SQL support for registered datasets

English-to-SQL copilot still works

existing API shape mostly preserved

docs + tests + basic observability included

Decide what is explicitly out of scope for August:

full ANSI parity

DML/DDL beyond what product needs

full cost-based optimization work

enterprise auth/governance

Decide whether the old custom engine remains:

as fallback for narrow queries, or

as legacy/reference code only

Phase 1: Architecture decision
Write a short migration note in repo docs:

current custom engine role

target DataFusion role

what layers remain custom

Decide the execution model:

all /query/execute goes through DataFusion, or

route narrow SQL to custom engine and broad SQL to DataFusion

Decide the planning story for /query/plan:

keep current product-level plan only for narrow queries

return a simplified plan summary for broad queries

optionally expose DataFusion EXPLAIN

Decide error normalization strategy:

parse/validation errors from product layer

engine planning/execution errors normalized from DataFusion

Phase 2: Bring in DataFusion
Add datafusion dependency and pin a known-good version.

Create a local spike script or scratch test that:

creates SessionContext

registers a small Arrow table

runs a simple SQL query

returns Arrow results

Verify the Python API you want to rely on:

SessionContext.sql(...)

collect()

to_arrow_table()

Arrow import/export path

Confirm that in-memory Arrow tables from your registry can be fed into the DataFusion path cleanly.

Phase 3: Build a DataFusion execution adapter
Create a new service/module, e.g.:

app/services/datafusion_runner.py

or app/core/engine/datafusion_adapter.py

Implement session creation lifecycle:

one context per request, or

reusable context with table re-registration strategy

Implement dataset registration from your DatasetRegistry into DataFusion context.

Support in-memory Arrow table registration first.

Add result conversion:

DataFusion result → Arrow table

Arrow table → existing ExecutionResult

Preserve output shape:

columns

rows

row_count

Add an engine field in execute responses if useful, e.g. "engine": "datafusion".

Phase 4: Route /query/execute through DataFusion
Update QueryService.execute() to use the DataFusion runner.

Keep current request contract stable if possible.

Ensure current working queries still pass:

simple projection

filter

alias

order by

group by

aggregates

limit

Add first broad-SQL smoke tests:

INNER JOIN

LEFT JOIN

HAVING

subquery in WHERE or FROM

UNION ALL

Phase 5: Redesign validation
Simplify validation so it no longer hand-implements full SQL semantics unnecessarily.

Keep product-level validation for:

query must be allowed statement type

datasets must be registered

tables/columns should be known where feasible

optional product guardrails

Remove or relax current blockers that assume narrow SQL only:

blanket join rejection

blanket multi-table rejection

over-strict aggregate restrictions when DataFusion can validate correctly

Decide whether validation should:

use SQLGlot for metadata extraction only, or

call DataFusion planning/EXPLAIN as part of validation

Normalize validation errors into your current API error shape.

Phase 6: Metadata and schema alignment
Make sure table metadata in your registry is the source of truth for:

table names

column names

descriptions

aliases

sample values if present

Ensure copilot schema context and execution engine use the same registered datasets.

Decide how DataFusion sees dataset names:

exact registry names

namespaced/catalog style names

Add tests that validate schema consistency between:

registry

catalog endpoints

copilot schema context

DataFusion registration

Phase 7: Catalog and ingestion
Finish CSV loading.

Finish Parquet loading.

Register loaded datasets automatically in the registry.

Store metadata:

row count

schema

source path

loaded timestamp

Add ingestion tests for:

CSV

Parquet

duplicate table names

invalid schema/file handling

If useful, support file-backed DataFusion registration for loaded datasets:

register_csv

register_parquet

Phase 8: Broaden SQL capability tests
Add execute tests for joins:

inner join on equality

left join

join with alias references

Add execute tests for subqueries:

scalar subquery

IN (subquery)

subquery in FROM

Add tests for HAVING.

Add tests for UNION / UNION ALL.

Add tests for richer expressions:

arithmetic in SELECT

expressions in ORDER BY

expressions with aliases

Add window function tests if time allows:

ROW_NUMBER()

LAG()

SUM(...) OVER (...)

Phase 9: Copilot migration
Update prompt instructions to reflect broader SQL support.

Add few-shot examples for:

joins

grouped queries with HAVING

subqueries

union queries

Update repair prompts so they no longer over-reject joins if joins are now supported.

Keep product safety rules explicit in the prompt:

only registered datasets

no made-up columns

prefer simple valid SQL

Expand eval coverage:

multi-table join requests

ambiguous join requests

hallucinated join keys

grouped + having requests

nested subquery requests

Track category metrics for broad-SQL copilot quality.

Phase 10: Error handling and UX
Normalize DataFusion parse/planning/execution errors into your API error format.

Keep error messages user-friendly:

unknown table

unknown column

ambiguous column

unsupported syntax if still applicable

Distinguish:

product validation failure

engine planning failure

runtime execution failure

Add tests for broad-SQL failure cases:

unknown join table

unknown join column

ambiguous column name

malformed subquery

Phase 11: Observability
Standardize debug metadata across:

/query/validate

/query/plan

/query/execute

Add stage timings:

validate

copilot_generate

copilot_repair

execute

Add structured logs for:

request id

normalized sql

engine used

status/outcome

Add minimal OTEL spans around:

validation

execution

copilot generation/repair

Phase 12: Benchmarks
Build a benchmark script comparing:

current custom engine

DataFusion-backed execution

Benchmark core query classes:

filter/project/limit

aggregate/group by

order by + limit

join

Benchmark at increasing sizes:

1k

10k

100k

1M rows

Save benchmark summaries to disk.

Add simple regression thresholds or at least manual benchmark baselines.

Phase 13: Docs
Update README.md for DataFusion-backed broad SQL execution.

Update DEVELOPMENT.md:

supported SQL surface

what is validated by product layer vs engine layer

current limitations

Add a migration note:

why DataFusion was adopted

what parts of the original custom engine remain

Add examples:

join query

subquery

having query

union query

copilot NL → SQL examples

Document known limitations honestly.

Phase 14: Release prep
Run full test suite cleanly.

Add at least one end-to-end demo scenario over 2–3 datasets.

Verify copilot + execute path with broad SQL examples.

Clean old TODOs and docs so they reflect the new architecture.

Tag a release candidate for August delivery.

First 14-day execution plan
Days 1–2
Freeze scope and write migration note.

Decide:

all execute via DataFusion, or hybrid

/query/plan behavior for broad SQL

Days 3–4
Add DataFusion dependency.

Create spike script:

register Arrow table

run SQL

collect results

Days 5–6
Create DataFusion adapter module.

Register tables from DatasetRegistry.

Convert results to current execution response shape.

Days 7–8
Route /query/execute through DataFusion.

Keep existing simple execute tests green.

Days 9–10
Add broad-SQL smoke tests:

join

having

union

subquery

Days 11–12
Relax/rewrite validator for broad SQL.

Normalize DataFusion errors.

Days 13–14
Update copilot prompt/rules for joins and broader SQL.

Add first broad-SQL copilot eval cases.

Definition of done for August
Users can query registered datasets with broad analytical SQL through the same API.

Copilot can generate valid SQL for common single-table and multi-table questions.

Validation still protects schema correctness and product rules.

Results return in a stable documented response shape.

Catalog/ingestion is usable for real CSV/Parquet datasets.

Basic logs, timings, benchmarks, and docs are in place.