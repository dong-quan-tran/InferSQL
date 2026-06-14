Backend Next Steps
The current InferSQL backend is now in a strong pre-LLM state: query validation, planning, execution, typed API contracts, structured error handling, dependency injection, observability, and component-level tests are in place.

Future Improvements
Add richer dataset metadata support beyond raw pyarrow.Table objects if feature-serving or catalog annotations become important later.

Add response examples and richer OpenAPI descriptions for query success and error cases to improve client integration and docs UX.

Expand executor capabilities incrementally, such as broader predicate support, ordering, joins, and multi-table planning, only after preserving the current deterministic contract.

Add performance-oriented work later, such as benchmarks, profiling, and possibly larger-than-memory Arrow dataset support if the engine grows beyond the current in-memory scope.

Introduce the LLM layer only as a separate orchestration layer for NL-to-SQL, ranking, and guidance, with this backend remaining the deterministic execution boundary.