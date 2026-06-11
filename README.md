# InferSQL

InferSQL is a unified data and AI platform that combines a vectorized SQL query engine, a low-latency model inference runtime, an LLM copilot, and end-to-end observability into one project.

The goal is to build something that feels closer to internal infrastructure at a quant firm or AI-native company than a typical portfolio CRUD app.

## Overview

At a high level, InferSQL brings together four capabilities:

- A vectorized query engine for analytical SQL execution over columnar data.
- A feature serving and inference layer for low-latency ML predictions.
- An LLM copilot for natural language to SQL, plan explanations, and operational workflows.
- An observability stack built around traces, metrics, and logs correlated by request ID.

The project is designed to showcase systems engineering, backend architecture, performance benchmarking, and production-minded AI integration in one codebase.

## Core ideas

### Vectorized query execution

InferSQL executes queries using columnar batches instead of processing one row at a time. The engine is intended to support a SQL pipeline of parsing, logical planning, physical planning, and execution with operators such as scan, filter, project, aggregate, sort, limit, and joins.

### Low-latency inference

The platform also includes an inference runtime with model registration, versioning, and controlled rollout strategies such as direct, shadow, canary, A/B, and rollback modes. Feature lookup is designed around an online store for fast retrieval and an offline computation path that integrates with the query engine itself.

### LLM copilot

The copilot layer is meant to do more than chat. It translates natural language into safe SQL, explains execution plans, answers observability questions, and helps operate model deployments with confirmation and guardrails.

### Observability

InferSQL is instrumented around the three pillars of observability: traces, metrics, and logs. The intended setup uses OpenTelemetry for instrumentation, Prometheus for metrics, Grafana for dashboards, Tempo for tracing, and Loki for logs, with `request_id` used to correlate activity across the stack.

## Architecture

InferSQL is organized around a control plane and a data plane, with the copilot and observability layers spanning the system.

```text
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
│  │  Vectorized Operators (Arrow Record Batches)    │   │
│  │  Scan · Filter · Project · Agg · Hash Join      │   │
│  └────────────────────┬────────────────────────────┘   │
│                       │                                │
│  ┌────────────────────▼────────────────────────────┐   │
│  │         FEATURE SERVING LAYER                   │   │
│  │  Online Feature Store · Offline Cache           │   │
│  │  Feature Registry · Versioned Feature Sets      │   │
│  └────────────────────┬────────────────────────────┘   │
│                       │                                │
│  ┌────────────────────▼────────────────────────────┐   │
│  │         INFERENCE RUNTIME                       │   │
│  │  Model Serving · Canary Router · Shadow Engine  │   │
│  │  Rollback · Batch Jobs                          │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────┐
│                   LLM COPILOT LAYER                    │
│  NL→SQL · Plan Explainer · Observability Assistant     │
│  Inference Commander · Guardrails                      │
└───────────────────────────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────┐
│                OBSERVABILITY STACK                     │
│  OpenTelemetry · Prometheus · Grafana · Tempo · Loki  │
└───────────────────────────────────────────────────────┘
```

## Repository structure

The project is organized around engine, inference, control plane, copilot, observability, frontend, configuration, tests, and docs.

```text
infersql/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       │   ├── engine/
│       │   ├── inference/
│       │   └── observability/
│       └── schemas/
├── frontend/
├── configs/
├── tests/
├── scripts/
└── docs/
```

The exact layout may evolve as implementation changes, but the core system boundaries remain the same: query execution, serving, copilot, and observability.

## Features

Current and planned project capabilities include:

- SQL parsing, validation, planning, and execution.
- Logical and physical plan generation.
- Vectorized operators over columnar batches.
- Request-scoped debug metadata and timing breakdowns.
- OpenTelemetry instrumentation for traces and metrics.
- Benchmark scripts for repeatable performance measurement.
- Model registry and deployment workflows.
- Online feature retrieval for inference.
- Guardrailed natural-language-to-SQL workflows.
- Dashboard and API surfaces for operational visibility.

## Example query flow

A typical query path in InferSQL looks like this:

1. A client sends SQL or a natural-language request.
2. The request is validated and normalized.
3. SQL is parsed into an abstract syntax tree.
4. A logical plan is produced and optimized.
5. A physical plan is built from executable operators.
6. The engine executes over columnar data batches.
7. Results, plans, debug timings, and observability signals are returned or emitted.

This structure makes the project useful both as an application and as a learning artifact for database internals and backend systems design.

## Tech stack

InferSQL is built around a modern Python-first systems stack.

| Area | Technology |
|---|---|
| Backend API | FastAPI |
| Query engine data model | Apache Arrow / PyArrow |
| Model serving | ONNX Runtime, PyTorch |
| Feature store | Redis |
| Metadata store | PostgreSQL |
| Observability | OpenTelemetry, Prometheus, Grafana, Tempo, Loki |
| Frontend | React, TypeScript |
| Testing | pytest, Hypothesis |
| Containerization | Docker Compose |

## Development goals

InferSQL is intended to demonstrate strong engineering signals in several areas:

- Database internals, including planning and vectorized execution.
- Low-latency backend design and performance measurement.
- ML platform workflows such as registration, rollout, and rollback.
- Production observability with correlated traces, metrics, and logs.
- Safe LLM integration with explicit operational guardrails.

That combination is what makes the project broader than a standalone query engine or a standalone model-serving demo.

## Benchmarks

Performance is a major part of the project story. Planned benchmark areas include:

- Vectorized query execution vs row-loop baselines.
- Query operator timings and end-to-end request durations.
- Model inference throughput and P95/P99 latency.
- Feature store lookup latency.
- NL→SQL accuracy on a fixed evaluation set.
- Deployment rollback response time after drift detection.

As benchmark scripts mature, this README can be updated with concrete numbers.

## API direction

The platform is designed around a backend API that exposes query, model, deployment, feature, and observability workflows. Depending on the stage of implementation, endpoints may include validation, planning, execution, natural-language query translation, model registration, deployment updates, rollback, and metrics or drift inspection.

## Observability and debugging

A major design goal of InferSQL is that internal behavior should be inspectable, not hidden. Requests are intended to carry a request ID across layers, emit latency metrics, and expose enough plan and execution detail to support debugging, benchmarking, and performance tuning.

Recent backend work also supports request-level debug timing metadata and a separation between HTTP request timing and query-specific timing.

## Why this project matters

InferSQL is meant to show the ability to work across multiple layers of a modern backend system rather than only building API endpoints. It combines systems programming concepts, ML infrastructure patterns, operational tooling, and AI-assisted workflows in a way that is useful for both learning and portfolio presentation.

## Running locally

Local setup will depend on which parts of the stack are implemented, but a typical developer workflow looks like this:

```bash
# create and activate virtual environment
python -m venv .venv

# install dependencies
pip install -r requirements.txt

# run the backend API
uvicorn app.main:app --reload
```

If the full local stack is enabled, Docker Compose can be used to start supporting services such as PostgreSQL, Redis, Prometheus, Grafana, and the OpenTelemetry collector.

```bash
docker compose up --build
```

## Roadmap

The project roadmap includes:

- Foundation and local infrastructure.
- Core query engine operators.
- SQL parser and planner.
- Feature store integration.
- Model registry and inference runtime.
- Deployment routing and rollback logic.
- Drift detection and observability expansion.
- LLM copilot workflows.
- Frontend integration.
- Benchmarks, documentation, and CI polish.

## Status

InferSQL is an active build in progress. Some parts of the platform are already implemented, while others remain planned or partially scaffolded. The long-term vision is a cohesive system where analytical queries, inference, observability, and AI assistance all work together through a unified interface.

