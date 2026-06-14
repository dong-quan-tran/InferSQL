# Backend Structural Improvements TODO

This document outlines the next structural improvements for the current InferSQL backend before adding any LLM layer. The priorities focus on making the backend predictable, testable, typed, and easier to extend, especially around the current SQL validation, planning, and execution pipeline.[1][2]

## Goals

The current backend already has the core query-engine flow in place: request handling, SQL validation, planning, execution, dataset registry access, and Arrow-backed results. The next step is not adding more features immediately, but reducing architectural ambiguity so future work such as LLM-assisted query generation plugs into a stable system rather than compensating for inconsistent boundaries or error handling.[1][3]

## Priority Overview

| Priority | Area | Why it matters |
|---|---|---|
| P0 | Domain exceptions and error handling | Prevents internal errors from leaking through the API and gives clients stable failure contracts.[4][5] |
| P0 | Dependency injection | Makes services easier to test, replace, and wire consistently in FastAPI.[6][2] |
| P1 | Clear query-engine boundaries | Keeps parser, validator, planner, and executor responsibilities separate and easier to maintain.[1][3] |
| P1 | Typed request/response contracts | Reduces drift between implementation, tests, and API documentation.[6][7] |
| P2 | Deeper component-level tests | Catches regressions inside engine stages before they become endpoint failures.[1][8] |
| P2 | Observability and logging cleanup | Makes startup, request flow, and failures easier to debug in test and production environments.[9][10][5] |

## 1. Domain Exceptions and Error Mapping

### Objective

Replace generic exceptions such as `ValueError` and accidental infrastructure errors with explicit domain exceptions and centralized FastAPI handlers.[4][5][11]

### Tasks

- Create a dedicated exception module, for example `backend/app/core/errors.py`.
- Add domain exceptions such as:
  - `UnknownDatasetError`
  - `UnknownColumnError`
  - `UnsupportedQueryError`
  - `InvalidQuerySyntaxError`
  - `ExecutionError`
  - `PlanningError`
- Update `DatasetRegistry`, query validation, and execution code to raise these specific exceptions instead of generic `ValueError`.
- Add FastAPI exception handlers that translate domain exceptions into stable JSON responses.
- Standardize error payload shape, for example:

```json
{
  "error": {
    "code": "UNKNOWN_DATASET",
    "message": "Unknown dataset 'prices_daily'"
  }
}
```

- Ensure route handlers do not manually catch and reshape exceptions unless absolutely necessary.
- Add tests that verify status code, error code, and message shape for each common failure path.

### Definition of done

- No raw `AttributeError` or generic `ValueError` leaks through API responses.
- Every expected validation/planning/execution failure maps to a documented API error contract.[4][5]

## 2. Dependency Injection for Core Services

### Objective

Make the backend depend on explicit providers rather than implicit object construction inside route handlers or modules.[6][2][7]

### Tasks

- Add dependency provider functions such as:
  - `get_settings()`
  - `get_dataset_registry()`
  - `get_query_parser()`
  - `get_query_planner()`
  - `get_query_executor()`
  - `get_query_service()`
- Refactor FastAPI routes to use `Depends(...)` for service wiring.
- Avoid global mutable singletons unless they are explicitly intended and lifecycle-managed.
- Ensure test fixtures can override dependencies cleanly.
- Move seeding/bootstrap logic into lifespan startup or a dedicated bootstrap module instead of route-time initialization.

### Definition of done

- Routes are thin and mostly delegate work.
- Unit tests can replace the registry, planner, or executor without patching internals.[6][2]

## 3. Separate Query-Engine Stages More Clearly

### Objective

Turn `QueryService` into an orchestration layer rather than a catch-all for parsing, validation, planning, and execution behavior.[1][3]

### Tasks

- Audit `QueryService` and list everything it currently owns.
- Split responsibilities into dedicated collaborators, for example:
  - `SqlNormalizer`
  - `SchemaValidator`
  - `LogicalPlanner`
  - `PhysicalPlanner`
  - `QueryExecutorFacade` or `QueryRunner`
- Keep `QueryService` responsible only for endpoint-level orchestration and response shaping.
- Ensure each stage accepts well-defined inputs and returns typed outputs.
- Reduce direct cross-calls between unrelated layers, for example planner code reaching into route-specific concerns.

### Suggested target flow

1. Normalize SQL.
2. Parse SQL.
3. Validate query kind and referenced schema.
4. Build logical plan.
5. Build physical plan.
6. Execute plan.
7. Serialize result into response DTO.

### Definition of done

- Each pipeline stage has a narrow purpose and can be tested independently.[1][3]

## 4. Formalize Contracts with Typed Models

### Objective

Make request and response shapes explicit across API and internal engine boundaries.[6][7]

### Tasks

- Review all request models for `/query/validate`, `/query/plan`, and `/query/execute`.
- Add or refine Pydantic response models for:
  - validation result
  - planning result
  - execution result
  - API error result
- Create typed internal DTOs where helpful, such as:
  - `ValidationSummary`
  - `SchemaReferenceSummary`
  - `CompiledQuery`
  - `ExecutionResult`
- Ensure OpenAPI output matches actual route behavior.
- Remove ad hoc dictionaries where a model improves clarity.

### Definition of done

- The API contract is visible in code, docs, and tests, with less risk of accidental shape drift.[7][6]

## 5. Strengthen Dataset Registry Boundaries

### Objective

Stabilize the registry as a small but well-defined data access boundary for the in-memory Arrow tables.

### Tasks

- Keep registry naming consistent, for example supporting one canonical accessor and temporary compatibility aliases only where needed.
- Define clear registry responsibilities:
  - register a dataset
  - fetch a dataset
  - list available datasets
  - inspect schema metadata
- Add method-level tests for successful fetch, missing dataset behavior, and schema inspection.
- Decide whether the registry stores only `pyarrow.Table` objects or a richer dataset wrapper containing metadata.
- If metadata is needed later, introduce it deliberately rather than overloading table names.

### Definition of done

- Registry behavior is stable, explicit, and no longer a common source of interface mismatch bugs.

## 6. Expand Component-Level Test Coverage

### Objective

Move beyond endpoint-only confidence and test each engine stage directly.[1][8]

### Tasks

- Add parser tests for:
  - valid simple SELECT
  - invalid SQL syntax
  - non-SELECT rejection
  - table and column extraction
- Add schema validator tests for:
  - known dataset
  - unknown dataset
  - known column
  - unknown column
  - wildcard handling
- Add logical planner tests for:
  - projection nodes
  - filter nodes
  - limit nodes
  - single-table enforcement
- Add physical planner tests for:
  - operator ordering
  - scan → filter → project → limit pipeline
- Add executor tests for:
  - happy-path row retrieval
  - filter application
  - projection correctness
  - limit behavior
  - empty result handling
- Keep endpoint tests focused on contract behavior, not every internal detail.

### Definition of done

- Most regressions are caught before they surface as API failures.[1]

## 7. Logging and Observability Cleanup

### Objective

Make debugging easier during startup, requests, and execution failures using structured, stage-aware logs.[9][10][5]

### Tasks

- Standardize log fields such as:
  - `request_id`
  - `environment`
  - `route`
  - `stage`
  - `dataset`
  - `error_code`
- Ensure request middleware always injects a request ID.
- Add debug/info logs around parse, validate, plan, and execute stages.
- Log domain exceptions with consistent structure.
- Keep JSON logging optional via settings, but ensure plain-text and JSON modes expose the same useful fields.
- Avoid noisy logs in tests unless debugging is enabled.

### Definition of done

- Logs make it clear where a request failed without requiring deep traceback inspection.[9][10]

## 8. Lifespan and Bootstrap Hardening

### Objective

Make startup and shutdown predictable, especially around settings, telemetry, registry seeding, and test bootstrapping.

### Tasks

- Audit what happens in lifespan startup.
- Move startup concerns into explicit bootstrap functions where possible.
- Make demo-data seeding idempotent.
- Ensure startup failures raise domain-relevant boot errors instead of generic exceptions.
- Separate production startup concerns from test-only or local-development concerns where appropriate.

### Definition of done

- App startup is boring, repeatable, and easy to reason about in both tests and development.

## 9. Internal Naming and Package Consistency

### Objective

Reduce friction caused by inconsistent names across service, registry, executor, and tests.[7]

### Tasks

- Audit naming consistency for:
  - `env` vs `environment`
  - `get` vs `get_table`
  - `query_runner` vs `query_executor`
  - `compiled` vs `planned` vs `validated`
- Pick one canonical name per concept.
- Keep compatibility shims only where necessary and document them.
- Update code comments and tests to use the canonical vocabulary.

### Definition of done

- Code reads like one coherent system instead of a set of stitched-together iterations.[7]

## 10. Suggested Implementation Order

1. Domain exceptions and FastAPI error handlers.[4][5]
2. Dependency injection for registry, parser, planner, executor, and service.[6][2]
3. QueryService refactor into orchestration-only behavior.[1][3]
4. Typed request/response models and internal DTOs.[6][7]
5. Registry boundary cleanup and schema access helpers.
6. Component-level tests for parser, validator, planner, and executor.[1][8]
7. Logging and observability cleanup.[9][10]
8. Lifespan/bootstrap hardening.
9. Naming consistency pass.

## Milestone Checklist

- [ ] Domain exceptions introduced and wired to FastAPI handlers.
- [ ] API error payloads standardized.
- [ ] Dependency providers added for all core services.
- [ ] `QueryService` reduced to orchestration.
- [ ] Typed response models added for validate, plan, execute, and errors.
- [ ] Dataset registry responsibilities clarified and tested.
- [ ] Parser, validator, planner, and executor have dedicated unit tests.
- [ ] Logs contain consistent request and stage metadata.
- [ ] Lifespan/bootstrap flow simplified and stabilized.
- [ ] Naming inconsistencies cleaned up.

## Result

Once these improvements are complete, the backend should feel stable, explicit, and easier to extend. That is the right point to add an LLM layer, because the model can then sit on top of a well-defined validation and execution contract instead of becoming a workaround for backend ambiguity.[1][2][5]