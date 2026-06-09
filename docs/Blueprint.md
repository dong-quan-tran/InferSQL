# InferSQL — Complete 6–8 Week Build Blueprint
### A Unified Vectorized Query Engine + Low-Latency AI Inference Platform with LLM Copilot

***

## Executive Summary

**InferSQL** is a production-style unified platform that combines three sophisticated systems into one cohesive architecture:

1. **A vectorized analytical query engine** — processes columnar batches of data instead of row-by-row, mirroring the internals of DuckDB and ClickHouse[^1][^2]
2. **A low-latency ML inference and feature-serving platform** — handles model registration, versioning, canary/shadow deployment, and online feature lookup[^3][^4]
3. **An LLM copilot layer** — translates natural language into safe SQL, explains query plans, and surfaces observability insights[^5][^6][^7]

The platform is not a toy. It is designed to look and feel like internal infrastructure at a quant firm or AI-native tech company — the kind that Two Sigma or Citadel SWEs would build in-house. By the end of 8 weeks, you will have a system with:[^8][^9]

- a working vectorized query engine with benchmarks against naive row-based execution
- a model serving runtime with canary, shadow, and rollback deployment modes
- a full OpenTelemetry observability stack with Prometheus, Grafana, and distributed tracing
- an LLM-powered SQL and inference copilot with guardrails
- a React dashboard, gRPC/REST API, Docker Compose deployment, and a clean public GitHub

***

## The One-Paragraph Pitch

> InferSQL is a unified AI data plane that allows analysts and ML engineers to query analytical datasets with vectorized SQL, retrieve online features for real-time inference, and deploy versioned ML models — all through one platform. An LLM copilot translates natural language into safe SQL queries, explains execution plans, and surfaces production anomalies. The platform is instrumented end-to-end with OpenTelemetry, exposing traces, metrics, and logs through a Grafana dashboard.

That is what you say to a recruiter in one breath.

***

## Why This Project Is Extraordinary

Most student SWE projects stop at CRUD apps or basic REST APIs. InferSQL signals maturity across five dimensions that quant SWE recruiters at Jane Street, Two Sigma, Citadel, HRT, and top tech companies care about:

| Signal | What it demonstrates |
|---|---|
| Database internals | You understand columnar storage, vectorized operators, and query planning[^2][^1] |
| Low-latency systems | You built a model serving path that minimizes P99 latency[^10] |
| Production ML infra | You know canary, shadow, A/B deployment, and drift detection[^3][^11] |
| Observability engineering | You instrumented a distributed system with traces, metrics, and logs[^12][^13] |
| AI integration | You built a guardrailed LLM interface — not a toy chatbot[^6][^14] |

***

## Architecture Overview

InferSQL has two planes and three major subsystems.

```
┌───────────────────────────────────────────────────────┐
│                   CONTROL PLANE                        │
│  Model Registry · Deployment Manager · Config Store    │
│  Admin API · Auth · Rate Limiting                      │
└───────────────────┬───────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────┐
│                    DATA PLANE                          │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │         VECTORIZED QUERY ENGINE                 │   │
│  │  SQL Parser → Logical Plan → Physical Plan      │   │
│  │  Vectorized Operators (Arrow Record Batches)     │   │
│  │  Scan · Filter · Project · Agg · Hash Join      │   │
│  └────────────────────┬────────────────────────────┘   │
│                       │                                │
│  ┌────────────────────▼────────────────────────────┐   │
│  │         FEATURE SERVING LAYER                   │   │
│  │  Online Feature Store (Redis) · Offline Cache   │   │
│  │  Feature Registry · Versioned Feature Sets      │   │
│  └────────────────────┬────────────────────────────┘   │
│                       │                                │
│  ┌────────────────────▼────────────────────────────┐   │
│  │         INFERENCE RUNTIME                       │   │
│  │  ONNX/PyTorch Model Serving · Batch Jobs        │   │
│  │  Canary Router · Shadow Engine · Rollback       │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────┐
│                   LLM COPILOT LAYER                    │
│  NL→SQL Agent · Query Plan Explainer                   │
│  Observability Assistant · Inference Commander        │
│  Guardrail Validator · Schema-Aware Prompts           │
└───────────────────────────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────┐
│            OBSERVABILITY STACK                         │
│  OpenTelemetry Collector · Prometheus · Grafana Tempo  │
│  Loki (Logs) · Request Tracing · Drift Monitors       │
└───────────────────────────────────────────────────────┘
```

***

## Repository Structure

```
infersql/
├── core/
│   ├── engine/
│   │   ├── parser/             # SQL lexer and parser
│   │   ├── planner/            # Logical and physical plan builder
│   │   ├── executor/           # Vectorized operator implementations
│   │   │   ├── scan.py
│   │   │   ├── filter.py
│   │   │   ├── project.py
│   │   │   ├── aggregate.py
│   │   │   └── join.py
│   │   └── catalog/            # Schema and table metadata
│   ├── feature_store/
│   │   ├── registry.py
│   │   ├── online_store.py     # Redis-backed low-latency lookup
│   │   └── offline_store.py    # Columnar batch reads
│   └── inference/
│       ├── runtime.py          # ONNX/PyTorch inference core
│       ├── registry.py         # Model registry + metadata
│       ├── router.py           # Canary / shadow / A-B routing
│       ├── drift_detector.py   # PSI + KS tests
│       └── batch_runner.py
├── control_plane/
│   ├── api/                    # FastAPI routers
│   │   ├── query.py
│   │   ├── models.py
│   │   ├── features.py
│   │   ├── deployments.py
│   │   └── admin.py
│   ├── auth.py
│   └── rate_limiter.py
├── copilot/
│   ├── nl_to_sql.py            # LLM NL→SQL agent
│   ├── plan_explainer.py       # Query plan explanation
│   ├── obs_assistant.py        # Observability Q&A
│   ├── inference_commander.py  # NL→serving commands
│   └── guardrails.py           # Safety validator
├── observability/
│   ├── telemetry.py            # OTel setup
│   ├── metrics.py              # Prometheus metrics
│   └── drift_monitor.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── QueryWorkbench.tsx
│   │   │   ├── ModelRegistry.tsx
│   │   │   ├── Deployments.tsx
│   │   │   ├── Observability.tsx
│   │   │   └── Copilot.tsx
│   │   └── components/
├── configs/
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   ├── otel-collector.yml
│   └── grafana/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
└── docs/
    ├── architecture.md
    ├── query-engine.md
    └── inference-runtime.md
```

***

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Query engine core | Python + PyArrow[^15][^16] | Apache Arrow provides zero-copy columnar batches — the ideal data structure for vectorized operators |
| Feature store cache | Redis[^17][^18] | Sub-millisecond keyed lookups for online feature retrieval |
| Model serving | ONNX Runtime + PyTorch[^19][^10] | ONNX Runtime delivers up to 9x throughput improvement over raw PyTorch[^10] |
| API layer | FastAPI + gRPC | FastAPI for REST; gRPC for high-throughput inference paths |
| Metadata DB | PostgreSQL | Model registry, deployment history, audit logs |
| Observability | OpenTelemetry + Prometheus + Grafana + Tempo + Loki[^12][^13] | Full three-pillar observability — traces, metrics, logs |
| LLM layer | Local LLM via Ollama (or OpenAI API) | Schema-aware prompting, guardrailed SQL generation[^14][^6] |
| Frontend | React + TypeScript + Recharts | Clean dashboard and workbench |
| Containerization | Docker Compose | Single-command local deployment |
| Testing | pytest + Hypothesis (property-based) | Property-based testing for query engine correctness |
| CI/CD | GitHub Actions | Automated test + lint pipeline |

**Language note:** The query engine executor is the performance-critical hot path. Write it in pure Python first and benchmark it. Then, if you want to go further, implement the hot loops in Rust with PyO3 bindings. This is a very strong stretch goal — it demonstrates polyglot systems engineering.[^10]

***

## Subsystem Deep Dives

### Subsystem 1: Vectorized Query Engine

**Core concept:** A vectorized engine processes data in columnar batches of 1,024–4,096 values per operator call instead of one row at a time, achieving dramatically better CPU cache utilization and SIMD instruction throughput.[^2]

Apache Arrow provides the in-memory columnar format (`RecordBatch`). Each operator receives an Arrow `RecordBatch`, applies its transformation, and returns a new `RecordBatch`. The query planner chains these operators into a physical plan tree.[^20][^15]

**SQL Dialect to support (MVP):**
```sql
SELECT col_a, SUM(col_b) AS total
FROM dataset_name
WHERE col_c > 100
GROUP BY col_a
ORDER BY total DESC
LIMIT 10
```

**Operator set (in order of implementation):**

1. `TableScan` — reads data from Parquet or CSV into Arrow RecordBatches
2. `Filter` — applies boolean predicate mask over a batch
3. `Project` — selects and renames columns
4. `Aggregate` — hash-based GROUP BY with accumulator pattern
5. `Sort` — external merge sort for ORDER BY
6. `Limit` — pass-through with row count
7. `HashJoin` — build hash table on left side, probe with right side
8. `NestedLoopJoin` — fallback for non-equi joins

**Logical plan → physical plan:**

The planner builds an AST from the SQL parser, performs rule-based optimizations (predicate pushdown, projection pruning), then maps each logical node to a physical operator. This is where the "query optimizer" lives.

**Benchmarking requirement:** After building the engine, write a benchmark that compares your vectorized engine against a naive Python row-by-row loop on the same dataset (10M rows, aggregation query). The speedup number goes in your README and résumé bullets.

**Key technical detail — predicate pushdown:** Move filter conditions as close to the table scan as possible so fewer rows travel through the pipeline. This is the single most impactful optimization and also the most important concept to explain in interviews.

***

### Subsystem 2: Online Feature Store + Inference Runtime

**Feature store design:**

The online store uses Redis as the backing key-value database for sub-millisecond feature retrieval. Features are stored as `{entity_id}:{feature_set_name}:{version}` keys with serialized JSON or MessagePack values. The offline store uses the query engine itself for batch feature computation — this is the elegant integration point that ties the two subsystems together.[^17][^21][^18]

**Feature registry:**
- Feature definition schema: name, entity key, value type, freshness SLA, compute logic
- Historical materialization job: runs a SQL query through the vectorized engine, materializes results to Redis
- Freshness monitor: tracks last-updated timestamp per feature key

**Inference runtime architecture:**

The runtime manages the full lifecycle of a deployed model, from registration to retirement.[^22][^3]

```
Incoming Request
    │
    ▼
Traffic Router ──────────────────────────────────────────┐
    │                                                     │
    │ (100% production traffic)              (duplicate)  │
    ▼                                                     ▼
Champion Model                               Shadow Model
    │                                            │
    ▼                                            ▼
Response returned                     Prediction logged
to client                              (not returned to client)
```

**Deployment modes:**

| Mode | Description | When to use |
|---|---|---|
| **Direct** | 100% traffic to single model version | Default production |
| **Shadow** | Duplicate traffic; shadow model results logged only[^3][^23] | Safe validation of new model on live traffic |
| **Canary** | X% to new version, (100-X)% to champion[^22][^24] | Gradual production rollout |
| **A/B** | Split by user segment or request ID | Formal experiment between versions |
| **Rollback** | Instantly re-route 100% to prior champion | Automatic on drift threshold breach |

**Drift detection:** After each inference batch, compute Population Stability Index (PSI) on prediction distributions and Kolmogorov-Smirnov tests on input feature distributions. If PSI > 0.2 or KS p-value < 0.05, trigger an alert and escalate to automatic rollback if configured.[^25][^26][^27]

```python
# Drift detection flow (pseudocode)
baseline_dist = load_training_distribution(model_id)
current_dist = get_recent_predictions(model_id, window="1h")
psi = compute_psi(baseline_dist, current_dist)
ks_stat, ks_pval = scipy.stats.ks_2samp(baseline_dist, current_dist)

if psi > 0.2 or ks_pval < 0.05:
    emit_alert(model_id, severity="high", metrics={"psi": psi})
    if auto_rollback_enabled:
        deployment_manager.rollback(model_id)
```

**ONNX Runtime integration:**

Export all models to ONNX format at registration time. The inference runtime always loads `.onnx` files, making it framework-agnostic — it accepts scikit-learn, XGBoost, LightGBM, and PyTorch models equally after export. Benchmark the ONNX path against the raw PyTorch path: ONNX Runtime achieves 255 requests/second vs PyTorch's 35 requests/second in comparable setups.[^19][^10]

***

### Subsystem 3: LLM Copilot Layer

This is the AI/LLM component — but designed to be professional and safe, not a demo.[^14][^6]

**Four agents, each with a distinct scope:**

#### Agent 1: NL → SQL Agent
Translates natural language questions into safe, schema-bounded SQL queries.[^6][^14][^5]

**Guardrail pipeline:**
```
User question
    │
    ▼
Intent detector ──── (is this a SQL question or general chat?) ────► chat response
    │
    ▼
Schema injector (inject only relevant tables + columns)
    │
    ▼
LLM SQL generation (schema-bounded prompt)
    │
    ▼
Static validator (sqlglot parse check + SELECT-only enforcement)
    │
    ▼
Cost estimator (row count estimate, query complexity warning)
    │
    ▼
Execution preview ("This will scan ~2.3M rows. Proceed?")
    │
    ▼
Query execution via vectorized engine
    │
    ▼
Result + explanation returned to user
```

Key guardrails per production security recommendations:[^28]
- SELECT-only enforcement (no INSERT, UPDATE, DELETE, DROP)
- Schema-bounded prompting: LLM only sees table names and columns relevant to the question
- Row limit + timeout enforcement
- Static SQL validation before execution
- Prompt injection detection and rejection
- Sensitive column masking (certain columns hidden from LLM context)

#### Agent 2: Query Plan Explainer
Takes a physical execution plan tree and explains it in plain English. Identifies the most expensive operator, suggests whether an index or pre-aggregation would help, and flags common patterns like cross-joins or missing predicate pushdown.[^7][^29][^30]

Recent research shows LLM-based plan similarity matching can achieve 21% average query latency reduction by recommending better execution hints. The agent implements a simplified version of this using execution plan embeddings and semantic comparison.[^7]

#### Agent 3: Observability Assistant
Answers questions like:
- "Why did P99 latency spike at 2 AM?"
- "Which model version has the highest drift score this week?"
- "What is the bottleneck operator in my last 10 queries?"

Uses structured data from Prometheus metrics and Tempo traces as context, injected into the LLM prompt. The LLM does not directly query the database — it receives pre-computed telemetry summaries as structured context.[^12]

#### Agent 4: Inference Commander
Translates natural language deployment instructions into structured API calls with confirmation step:
- "Deploy fraud_model v3 in shadow mode against v2"
- "Increase canary weight of scoring_model v5 to 30%"
- "Roll back churn_model to the previous version"

Always shows the API call that will be executed before running it. Never executes destructive operations without explicit user confirmation.

***

### Subsystem 4: Observability Stack

Full three-pillar observability — traces, metrics, and logs — correlated by `request_id` through every layer of the platform.[^13][^12]

**Traces (OpenTelemetry → Grafana Tempo):**
- Every query request creates a root span: `query.execute`
- Child spans for each physical operator: `operator.scan`, `operator.filter`, `operator.aggregate`
- Child spans for feature lookups: `feature.redis_get`
- Child spans for inference calls: `inference.onnx_run`
- Parent-child relationships enable flamegraph visualization[^31][^12]

**Metrics (Prometheus → Grafana):**

| Metric | Type | Description |
|---|---|---|
| `infersql_query_duration_seconds` | Histogram | Query execution time by query type |
| `infersql_operator_rows_processed` | Counter | Rows processed per operator per batch |
| `infersql_inference_latency_seconds` | Histogram | Inference P50/P95/P99 per model version |
| `infersql_feature_cache_hit_ratio` | Gauge | Redis cache hit ratio per feature set |
| `infersql_model_drift_psi` | Gauge | Current PSI score per model |
| `infersql_deployment_traffic_pct` | Gauge | Traffic percentage per model version |
| `infersql_llm_query_count` | Counter | NL→SQL requests by intent type |

**Logs (structured JSON → Grafana Loki):**

Every log record includes `request_id`, `trace_id`, `model_id`, `query_id`, and `severity` fields. This allows correlation of a latency spike in a Prometheus metric to a specific trace in Tempo to a specific log entry in Loki — all by `request_id`.[^12][^13]

**Dashboard panels (Grafana):**
- Query throughput and latency heatmap
- Top-N slowest queries (by average duration)
- Model inference latency by version (overlaid for comparison)
- Drift score time series per model
- Feature store hit/miss ratio
- LLM copilot usage stats
- Active deployment mode per model

***

## Week-by-Week Execution Plan

### Week 1 — Foundation & Infrastructure

**Goal:** Repo skeleton, dev environment, data ingestion, and schema catalog.

**Tasks:**
- Initialize GitHub repo with branch protection, pre-commit hooks (`black`, `ruff`, `mypy`)
- Set up Docker Compose with PostgreSQL, Redis, Prometheus, Grafana, OTel Collector
- Design and create PostgreSQL schema: `models`, `deployments`, `feature_sets`, `query_history`, `drift_events`
- Build `DatasetLoader`: ingest Parquet and CSV files into in-memory Arrow Tables[^15]
- Build `SchemaRegistry`: register datasets with column names, types, and row counts
- Write test fixtures: 3 sample datasets (1K, 100K, 10M rows)
- Configure OpenTelemetry SDK and emit first test spans[^32][^31]

**Milestone acceptance:** `docker-compose up` brings up all services; schema registry stores and retrieves dataset metadata; OTel spans appear in Grafana Tempo.

***

### Week 2 — Vectorized Query Engine (Core Operators)

**Goal:** Working scan, filter, project, and limit operators on Arrow RecordBatches.

**Tasks:**
- Implement `RecordBatch`-based `TableScan` operator with columnar reads from Parquet[^16][^15]
- Implement `Filter` operator: boolean mask applied to batch — zero-copy where possible[^20]
- Implement `Project` operator: column selection and aliasing
- Implement `Limit` operator: pass-through with row counter
- Build a minimal `Interpreter` that chains operators manually (no planner yet)
- Write unit tests for every operator: correctness on small datasets, edge cases (empty batches, null values, single-row batches)
- Benchmark `Filter + Project + Limit` against naive Python loop on 1M rows
- Add operator-level OTel spans with `rows_in`, `rows_out`, and `duration_ms` attributes

**Milestone acceptance:** Can execute `SELECT col_a, col_b FROM dataset WHERE col_c > 50 LIMIT 100` through manually chained operators; benchmark shows meaningful speedup.

***

### Week 3 — SQL Parser, Planner, and Aggregation

**Goal:** Full SQL→plan→execution pipeline with GROUP BY and ORDER BY.

**Tasks:**
- Build SQL lexer and recursive-descent parser for the MVP dialect (SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT)
- Build `LogicalPlan` tree: `LogicalScan`, `LogicalFilter`, `LogicalProject`, `LogicalAggregate`, `LogicalSort`, `LogicalLimit`
- Implement `PhysicalPlanner`: maps logical nodes to physical operators
- Implement **predicate pushdown** rule: moves filters to be children of scans
- Implement **projection pruning** rule: drops unreferenced columns early
- Implement `Aggregate` operator: hash-based group accumulation over Arrow batches
- Implement `Sort` operator: batch-merge sort for ORDER BY
- Write property-based tests with Hypothesis: generate random tables and queries, compare results against pandas/DuckDB as ground truth
- Run full benchmark: vectorized aggregate query vs pandas vs row-loop on 10M rows

**Milestone acceptance:** Can parse and execute `SELECT region, SUM(revenue) FROM sales WHERE year = 2024 GROUP BY region ORDER BY SUM(revenue) DESC`; results match DuckDB ground truth on all test cases.

***

### Week 4 — Feature Store + Model Registry

**Goal:** Working online feature store and model registration pipeline.

**Tasks:**
- Build `FeatureRegistry`: define feature sets as Python dataclasses with entity key, compute SQL, and freshness SLA
- Build `FeatureMaterializer`: runs compute SQL through the vectorized engine, writes results to Redis as `{entity_id}:{feature_set}:{version}` keys[^18][^17]
- Build `OnlineFeatureStore`: `get_features(entity_ids, feature_set)` with Redis bulk GET (`MGET`), Redis cache miss fallback to offline store
- Instrument feature lookups: OTel spans, Prometheus cache hit/miss counter
- Build `ModelRegistry`: register a model (name, version, framework, artifact path, input schema, expected output schema)
- Export test models (XGBoost, scikit-learn) to ONNX format[^19]
- Build `InferenceRuntime.predict(model_id, version, feature_vector)`: load ONNX session, run inference, return result + latency
- Write integration test: materialize features → fetch from online store → run inference

**Milestone acceptance:** Can register a model, materialize its required features, retrieve them from Redis in < 5ms, and run inference through ONNX Runtime.

***

### Week 5 — Deployment Engine + Drift Detection

**Goal:** Multi-mode deployment system and automated drift monitoring.

**Tasks:**
- Build `DeploymentManager`: create, update, and retire deployments with mode (direct, shadow, canary, A/B)
- Build `TrafficRouter`: given a `request_id`, decide which model version to serve based on current deployment config[^3][^22]
- Build `ShadowEngine`: for shadow deployments, duplicate request to shadow model, log prediction without returning to client[^23]
- Build `CanaryRouter`: route X% of traffic by hashing `request_id` modulo 100[^24]
- Build `DriftDetector`: compute PSI and KS test on sliding window of predictions vs training baseline[^26][^27][^11][^25]
- Build `AutoRollback`: subscribe to drift events, trigger rollback if PSI > threshold
- Expose deployment controls via FastAPI: `/deployments`, `/deployments/{id}/promote`, `/deployments/{id}/rollback`
- Emit drift score as Prometheus gauge: `infersql_model_drift_psi`
- Write chaos test: inject synthetic drift by modifying feature distributions mid-run, verify rollback triggers

**Milestone acceptance:** Can run a canary deployment with traffic split, inject simulated drift, observe PSI spike in Grafana, and trigger automatic rollback.

***

### Week 6 — LLM Copilot Layer

**Goal:** Guardrailed NL→SQL agent, plan explainer, and observability assistant.

**Tasks:**
- Build `GuardrailValidator`: SELECT-only check, sqlglot syntax validation, schema boundary enforcement, sensitive column filter[^14][^28]
- Build `NLtoSQLAgent`: schema-aware prompt construction, LLM call (Ollama local or API), output parse, repair loop on syntax error[^5][^6][^14]
- Build cost estimator: estimate rows scanned and operators required before execution; return warning to user if scan > 5M rows
- Build `QueryPlanExplainer`: serialize the physical plan tree to text, prompt LLM to explain it in plain English, identify most expensive node[^29][^7]
- Build `ObservabilityAssistant`: pull last 1h of Prometheus metrics and trace summaries, inject as structured context, answer latency/throughput questions
- Build `InferenceCommander`: translate NL deployment commands to structured API calls with a confirmation step
- Write adversarial tests: attempt prompt injection, SQL injection via NL, schema leak — verify all are blocked[^28]
- Add `copilot_request_count` and `copilot_latency_seconds` metrics

**Milestone acceptance:** Can ask "show me total revenue by region for Q4 2024" and receive correct SQL + result; prompt injection attempts are blocked; plan explainer correctly identifies filter vs aggregation as bottleneck.

***

### Week 7 — API, Frontend, and Full Integration

**Goal:** Complete REST API, React dashboard, and end-to-end integration tests.

**Tasks:**
- Complete FastAPI router coverage:
  - `POST /query` — execute SQL, return results
  - `POST /query/nl` — NL→SQL, execute, return results + generated SQL
  - `GET /query/{id}/plan` — return physical plan + explanation
  - `POST /models` — register model
  - `GET /models` — list models and versions
  - `POST /deployments` — create deployment
  - `PATCH /deployments/{id}` — update mode/traffic weight
  - `POST /deployments/{id}/rollback` — instant rollback
  - `GET /features/{feature_set}` — lookup features by entity IDs
  - `GET /metrics/drift` — return drift scores per model
- Build React frontend pages:
  - **Query Workbench**: SQL editor + NL input + result table + plan visualizer
  - **Model Registry**: register model, view versions, export status
  - **Deployments**: view active deployments, adjust canary weight, force rollback
  - **Observability**: embedded Grafana panels + copilot Q&A interface
  - **Copilot**: conversational interface for all four agents
- Write end-to-end integration tests: full query pipeline, full inference pipeline, drift rollback scenario
- Load test: send 1,000 concurrent inference requests, measure P99 latency

**Milestone acceptance:** All API endpoints return correct responses; React dashboard works end-to-end; load test shows P99 inference latency < 50ms on local hardware.

***

### Week 8 — Polish, Benchmarks, Documentation, and Portfolio Packaging

**Goal:** Production-grade finishing, benchmarks, and recruiter-facing deliverables.

**Tasks:**
- Write and run full benchmark suite:
  - Vectorized engine vs pandas vs row-loop: scan, filter, aggregate, join at 1M and 10M rows
  - ONNX Runtime vs PyTorch: throughput (req/sec) and P99 latency
  - Redis feature lookup: P50/P95/P99 at 1K/10K entity lookups
  - NL→SQL accuracy: manually label 50 questions, measure correct SQL generation rate
- Add missing test coverage to 80%+ line coverage
- Improve error handling: typed exceptions, structured error responses
- Add request validation: Pydantic models for all API inputs
- Containerize with multi-stage Docker builds for production-style images
- Write architecture documentation with component diagrams
- Write `CONTRIBUTING.md`, `DEVELOPMENT.md`, `ARCHITECTURE.md`
- Record a 90-second demo video: run a query in natural language → see execution plan → check observability dashboard → deploy a new model in canary mode → trigger drift → observe rollback
- Finalize résumé bullets (see below)
- Add GitHub Actions CI: `pytest`, `ruff`, `mypy` on every push

**Milestone acceptance:** Clean GitHub repo with comprehensive README; all benchmarks documented with numbers; CI green; Docker Compose brings up full stack with demo data pre-loaded.

***

## Benchmarks to Publish

These numbers make your README and résumé concrete and credible.

| Benchmark | Target | Notes |
|---|---|---|
| Vectorized vs row-loop (10M rows, aggregate) | > 10x speedup | Baseline: Python loop per row |
| ONNX Runtime vs PyTorch (throughput) | > 5x improvement | Per published benchmarks[^10] |
| Online feature store P99 latency | < 5ms | Redis MGET for 10 features |
| End-to-end inference P99 (feature lookup + inference) | < 20ms | Local Redis + ONNX |
| NL→SQL accuracy (50-question eval) | > 85% correct | Schema-bounded prompting[^5] |
| Drift rollback response time | < 30 seconds | From threshold breach to re-route |

***

## LLM Integration Design Principles

The LLM layer must feel like a professional tool, not a demo. These principles enforce that.[^6][^14][^28]

1. **The LLM never has direct database access.** It generates SQL that is validated before execution.
2. **Schema is always injected at the column level** — only the tables and columns relevant to the request are passed to the LLM, preventing schema leakage.[^14][^6]
3. **Every generated SQL is statically validated** with `sqlglot` before execution — syntax errors trigger a repair loop, not a crash.[^14]
4. **SELECT-only enforcement is structural**, not just a prompt instruction. A regex/AST check blocks non-SELECT statements regardless of what the LLM returns.[^28]
5. **Every LLM action is logged** — query, generated SQL, validation result, execution result — for audit and improvement.
6. **Cost estimation happens before execution** — the system warns users before running a scan over 5M rows.
7. **The Observability Assistant uses pre-computed summaries**, not raw database access. The LLM receives structured metrics context, not an open database connection.[^6]

***

## Stretch Goals (Post Week 8)

If you finish early or want to extend the project further:

| Stretch goal | What it adds | Difficulty |
|---|---|---|
| Rust vectorized operator hot path | Demonstrates polyglot systems engineering; PyO3 FFI[^10] | Hard |
| HashJoin operator | Completes the SQL engine for multi-table queries | Medium |
| Query result caching layer | Semantic hash of query → cached result | Medium |
| gRPC inference endpoint | Production-style binary protocol for inference[^4] | Medium |
| Fine-tuned NL→SQL model | Fine-tune a small model on your schema; compare to zero-shot | Hard |
| Kubernetes deployment | Production-style orchestration with autoscaling | Medium |
| LLM-based query plan optimizer | Implement LLM-PM pattern for hint-based optimization[^7] | Hard |
| Real-time streaming features | Kafka → Redis feature refresh pipeline | Hard |
| Multi-model ensemble serving | Route to ensemble, aggregate predictions | Medium |

***

## Resume Bullets (Draft)

Refine these after you have real benchmark numbers:

**Vectorized Query Engine:**
> Built a vectorized SQL query engine in Python using Apache Arrow RecordBatches, implementing scan, filter, project, aggregate, sort, and hash join operators with predicate pushdown optimization; benchmarked **>10x throughput improvement** over row-based execution on 10M-row analytical queries.[^2][^15]

**Inference & Deployment Platform:**
> Designed a production-style ML inference runtime with model versioning, canary/shadow/A/B deployment routing, and automated drift detection using PSI and KS-test statistics; implemented automatic rollback on threshold breach, serving models through ONNX Runtime at **>5x throughput** versus raw PyTorch.[^10][^26][^3]

**LLM Copilot:**
> Engineered a guardrailed NL→SQL LLM agent with schema-bounded prompting, static SQL validation, prompt injection prevention, and cost estimation; achieved **>85% query accuracy** on a 50-question evaluation set against the platform's own vectorized engine.[^28][^6][^14]

**Observability:**
> Instrumented the full platform with OpenTelemetry distributed tracing, Prometheus metrics, and structured JSON logs correlated by request_id across query execution, feature serving, and inference — surfaced through Grafana dashboards with trace, metric, and log correlation.[^13][^31][^12]

***

## How to Talk About This Project in Interviews

**The 30-second pitch:**
> "InferSQL is a unified data and AI platform I built from scratch. It has a vectorized SQL query engine that processes data in Arrow columnar batches — similar to how DuckDB works internally — an ML inference runtime with shadow and canary deployment modes, full OpenTelemetry observability, and an LLM copilot with guardrails that translates natural language into safe SQL. The whole thing is instrumented end-to-end with traces, metrics, and logs correlated by request ID."

**Questions you must be ready to answer:**
- "Walk me through how your vectorized executor works." → Explain record batches, columnar operators, zero-copy Arrow format, predicate pushdown.
- "How does your canary deployment differ from shadow deployment?" → Shadow: results logged not returned; canary: real traffic split by percentage.
- "What guardrails did you add to the NL→SQL agent and why?" → SELECT-only enforcement, schema boundary, sqlglot validation, cost estimator, prompt injection blocking.
- "What drift metrics did you use and why PSI over KL divergence?" → PSI is interpretable (< 0.1 stable, 0.1–0.2 moderate, > 0.2 significant); KS test is non-parametric and doesn't assume distribution shape.
- "What was your biggest engineering challenge?" → Pick either: making operator chaining composable without copying data, or making the NL→SQL guardrail robust against adversarial inputs.

***

## What to Name It

Strong names that sound like a real product:

- **InferSQL** — emphasizes the inference + SQL fusion
- **HelixDB** — sounds like a real database engine
- **VectorServe** — clear signal: vectorized + serving
- **Axiom Platform** — clean, professional
- **Catalyst** — analytics + inference catalyst

Pick one and own it throughout the repo, README, and demo.

---

## References

1. [DuckDB + Arrow: The Future of In-Memory Analytics](https://medium.com/@connect.hashblock/duckdb-arrow-the-future-of-in-memory-analytics-0afa1258c593) - Zero-copy data flows, faster notebooks, and warehouse-grade queries — on your laptop and beyond.

2. [What is vectorized query execution? - ClickHouse](https://clickhouse.com/resources/engineering/vectorized-query-execution) - Vectorized query execution processes batches of values, typically 1024 to 4096 per operator call, in...

3. [Shadow deployment vs. canary release of machine learning models](https://www.qwak.com/post/shadow-deployment-vs-canary-release-of-machine-learning-models) - Shadow deployment is a crucial stage because it is the first time we see how the model will perform ...

4. [Model serving architectures - by Maria Vechtomova](https://www.marvelousmlops.io/p/model-serving-architectures) - During inference, the model serving endpoint fetches features from the online store using a primary ...

5. [How Prompt Engineering Turned Natural Language into Production ...](https://dev.to/osmanuygar/how-prompt-engineering-turned-natural-language-into-production-ready-sql-queries-3afp) - TL;DR: We built SQLatte, an AI-powered natural language to SQL platform, and learned that 80% of the...

6. [AskDB: An LLM Agent for Natural Language Interaction with ... - arXiv](https://arxiv.org/html/2511.16131v1) - Novel methodologies for agentic database interaction, including a dynamic schema-aware prompting mec...

7. [Training-Free Query Optimization via LLM-Based Plan Similarity](https://arxiv.org/html/2506.05853v1)

8. [Quantitative Software Engineer: Portfolio Research Acceleration](https://careers.twosigma.com/careers/JobDetail/New-York-City-United-States-Quantitative-Software-Engineer-Portfolio-Research-Acceleration/13081) - Our engineers engage with research topics and cover new domains quickly; build deep expertise with T...

9. [Scalable Model Serving: An Architectural Overview](https://www.snowflake.com/en/blog/engineering/scalable-model-serving-architecture/) - Learn how Snowflake ML enables scalable model serving with low-latency inference, centralized govern...

10. [9x model serving performance without changing hardware : r/Python](https://www.reddit.com/r/Python/comments/1gm0flj/9x_model_serving_performance_without_changing/) - This project benchmarks basic PyTorch serving against ONNX Runtime in both Python and Rust, showcasi...

11. [Model Drift & Machine Learning - Arize AI](https://arize.com/model-drift/) - Drift measures the change between two distributions over time from training, validation, or even pro...

12. [Observability | FastAPI Production Guide - Patryk Golabek](https://patrykgolabek.dev/guides/fastapi-production/observability/) - How the FastAPI Chassis instruments every request with OpenTelemetry distributed tracing, Prometheus...

13. [blueswen/fastapi-observability](https://github.com/blueswen/fastapi-observability) - Observe FastAPI app with three pillars of observability: Traces (Tempo), Metrics (Prometheus), Logs ...

14. [NaturalQL - Guardrailed Natural Language → SQL](https://paolo-notaro.github.io/blog/naturalql) - A tiny but solid demo that turns natural language into safe SQL with guardrails, a cinema dataset, a...

15. [Apache Arrow | Apache Arrow](https://arrow.apache.org) - Apache Arrow defines a language-independent columnar memory format for flat and nested data, organiz...

16. [Demystifying Apache Arrow | Robin Linacre's blog](https://www.robinlinacre.com/demystifying_arrow/) - Arrow has its own in-memory storage format. · Data in Arrow is stored in-memory in record batches, a...

17. [Low Latency AI/ML Feature Serving With Redis Enterprise - Redis](https://redis.io/resources/low-latency-ai-ml-feature-serving-with-redis-enterprise/) - Learn how critical component of the modern AI/ML platform stack that enable consistent MLOps best pr...

18. [Feature stores | Redisredis.io › solutions › feature-stores](https://redis.io/feature-form/) - A virtual feature store for the modern AI stack

19. [ONNX Runtime for inferencing machine learning models now in ...](https://azure.microsoft.com/en-us/blog/onnx-runtime-for-inferencing-machine-learning-models-now-in-preview/) - Azure: Using the ONNX Runtime Python package, you can deploy an ONNX model to the cloud with Azure M...

20. [Streaming Columnar Data with Apache Arrow - Wes McKinney](https://wesmckinney.com/blog/arrow-streaming-columnar/) - In Apache Arrow, an in-memory columnar array collection representing a chunk of a table is called a ...

21. [Well-Architected Pillars](https://aws.amazon.com/solutions/guidance/ultra-low-latency-machine-learning-feature-stores-on-aws/) - This Guidance shows how you can build an ultra-low latency online feature store using Amazon ElastiC...

22. [How to Implement Canary Model Deployment - OneUptime](https://oneuptime.com/blog/post/2026-01-30-mlops-canary-model-deployment/view) - Learn to implement canary model deployment for gradual rollout of new ML models with traffic splitti...

23. [Shadow Deployment for ML Models: Strategy, Patterns and Risks](https://atlan.com/know/shadow-deployment-for-ml-models/) - Learn how shadow deployment tests ML models in production traffic without user impact. Covers archit...

24. [MLOps deployment best practices for real-time inference model ...](https://aws.amazon.com/blogs/machine-learning/mlops-deployment-best-practices-for-real-time-inference-model-serving-endpoints-with-amazon-sagemaker/) - The canary traffic shifting mode allows you to test your new model (green fleet) with a small portio...

25. [Data Drift vs Model Drift in Machine Learning Causes ... - YouTube](https://www.youtube.com/watch?v=0P25tVRg99s) - ... detect drift: PSI, statistical tests, performance monitoring - Best practices to prevent drift: ...

26. [How do you actually detect model drift in production? : r/mlops - Reddit](https://www.reddit.com/r/mlops/comments/1ppd9ro/how_do_you_actually_detect_model_drift_in/) - We went through this ended up using a combination of PSI for feature drift and custom embedding simi...

27. [What is concept drift in ML, and how to detect and address it](https://www.evidentlyai.com/ml-in-production/concept-drift) - Concept drift is a change in the relationship between the input data and the model target. It reflec...

28. [Natural language questions to my SQL database - n8n Community](https://community.n8n.io/t/natural-language-questions-to-my-sql-database/290999?tl=en) - In the SQL use case, the main concern is that prompt injection can push the model to generate unsafe...

29. [A Query Optimization Method Utilizing Large Language Models - arXiv](https://arxiv.org/html/2503.06902v1) - This paper presents LLMOpt, a novel framework that leverages Large Language Models (LLMs) to address...

30. [AI for Systems: Using LLMs to Optimize Database Query Execution](https://www.together.ai/blog/using-llms-to-optimize-database-query-execution) - New research shows LLMs can optimize database query execution plans—achieving up to 4.78x speedups b...

31. [A Complete Guide to Integrating OpenTelemetry with FastAPI | Last9](https://last9.io/blog/integrating-opentelemetry-with-fastapi/) - Learn how to integrate OpenTelemetry with FastAPI for enhanced observability, including automatic in...

32. [OpenTelemetry FastAPI Instrumentation and Monitoring](https://uptrace.dev/guides/opentelemetry-fastapi) - Add OpenTelemetry instrumentation to FastAPI apps using FastAPIInstrumentor.instrument_app(). Get au...

