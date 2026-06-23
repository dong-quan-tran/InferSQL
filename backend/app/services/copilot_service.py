from __future__ import annotations

import logging

from app.core.catalog.registry import DatasetRegistry
from app.schemas.copilot import (
    CopilotQueryResponse,
    CopilotRetryStep,
    CopilotSqlCandidate,
    CopilotValidationResult,
)
from app.services.copilot_schema_context import CopilotSchemaContextBuilder
from app.services.copilot_schema_selector import CopilotSchemaSelector
from app.services.llm.base import LLMProvider
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)


class CopilotService:
    def __init__(
        self,
        dataset_registry: DatasetRegistry,
        query_service: QueryService,
        llm_provider: LLMProvider,
        max_retries: int = 2,
    ) -> None:
        self.dataset_registry = dataset_registry
        self.query_service = query_service
        self.llm_provider = llm_provider
        self.max_retries = max_retries
        self.schema_context_builder = CopilotSchemaContextBuilder(dataset_registry)
        self.schema_selector = CopilotSchemaSelector(dataset_registry)

    def query(
        self,
        question: str,
        execute: bool = False,
        request_id: str | None = None,
    ) -> CopilotQueryResponse:
        schema_context = self._build_schema_context(question)
        retry_history: list[CopilotRetryStep] = []

        prompt_question = self._build_generation_prompt(
            question=question,
            schema_context=schema_context,
        )

        candidate = self.llm_provider.generate_sql_candidate(
            question=prompt_question,
            schema_context=schema_context,
        )
        validation = self._validate_candidate(candidate, request_id=request_id)

        attempt = 1
        while not validation.is_valid and attempt <= self.max_retries:
            retry_history.append(
                CopilotRetryStep(
                    attempt=attempt,
                    candidate=candidate,
                    validation=validation,
                )
            )

            logger.info(
                "copilot candidate rejected; retrying",
                extra={
                    "stage": "copilot_validate",
                    "request_id": request_id,
                    "attempt": attempt,
                    "errors": validation.errors,
                },
            )

            repair_question = self._build_repair_prompt(
                question=question,
                schema_context=schema_context,
                previous_candidate=candidate,
                validation=validation,
            )

            candidate = self.llm_provider.generate_sql_candidate(
                question=repair_question,
                schema_context=schema_context,
            )
            validation = self._validate_candidate(candidate, request_id=request_id)
            attempt += 1

        execution = None
        if execute and validation.is_valid:
            execution = self.query_service.execute(
                sql=candidate.sql,
                request_id=request_id,
                debug=False,
            )

        return CopilotQueryResponse(
            question=question,
            provider=self.llm_provider.provider_name,
            model=self.llm_provider.model_name,
            candidate=candidate,
            validation=validation,
            execution=execution,
            attempts=attempt,
            repaired=len(retry_history) > 0 and validation.is_valid,
            retry_history=retry_history,
        )

    def _validate_candidate(
        self,
        candidate: CopilotSqlCandidate,
        request_id: str | None = None,
    ) -> CopilotValidationResult:
        result = self.query_service.validate(
            sql=candidate.sql,
            request_id=request_id,
            debug=False,
        )

        return CopilotValidationResult(
            is_valid=result["is_valid"],
            normalized_sql=result["normalized_sql"],
            errors=result["errors"],
            tables=result["tables"],
            columns=result["columns"],
            query_type=result.get("query_type"),
            has_where=result["has_where"],
            has_group_by=result["has_group_by"],
            has_order_by=result["has_order_by"],
            has_limit=result["has_limit"],
        )

    def _build_schema_context(self, question: str) -> str:
        selected_tables = self.schema_selector.select_tables(question)
        return self.schema_context_builder.build(table_names=selected_tables)

    def _build_generation_prompt(self, question: str, schema_context: str) -> str:
        return (
            "Generate a SQL query for the user's question.\n\n"
            f"User question:\n{question}\n\n"
            f"Schema context:\n{schema_context}\n\n"
            "SQL capability rules:\n"
            "- Return only a SELECT query.\n"
            "- Use only the provided datasets and columns.\n"
            "- Multi-table SQL is allowed when needed, including INNER JOIN and LEFT JOIN.\n"
            "- Subqueries are allowed where supported, including IN subqueries, derived tables in FROM, and scalar subqueries.\n"
            "- UNION and UNION ALL are allowed where needed.\n"
            "- GROUP BY and HAVING are allowed where needed.\n"
            "- Do not use INSERT, UPDATE, DELETE, CREATE, DROP, or other non-SELECT statements.\n"
            "- Do not invent datasets, columns, or join keys.\n"
            "- Prefer explicit table aliases and qualify columns in multi-table queries.\n"
            "- If two tables share a column name, qualify the column reference.\n"
            "- Avoid ORDER BY on select-list aliases; order by the underlying column or expression instead.\n"
            "- Keep the query as simple as possible while correctly answering the question.\n"
        )

    def _build_repair_prompt(
        self,
        question: str,
        schema_context: str,
        previous_candidate: CopilotSqlCandidate,
        validation: CopilotValidationResult,
    ) -> str:
        error_lines = "\n".join(f"- {error}" for error in validation.errors) or "- Unknown validation error"
        lowered_errors = " ".join(validation.errors).lower()

        extra_guidance: list[str] = []

        if "ambiguous" in lowered_errors:
            extra_guidance.append(
                "- Fix ambiguous column references by qualifying them with table names or aliases."
            )

        if "unknown column" in lowered_errors:
            extra_guidance.append(
                "- Replace unknown columns only with real columns from the provided schema context."
            )

        if "unknown dataset" in lowered_errors or "unknown table" in lowered_errors:
            extra_guidance.append(
                "- Replace unknown datasets only with real datasets from the provided schema context."
            )

        if "join" in lowered_errors:
            extra_guidance.append(
                "- Do not invent join predicates; only use join keys that clearly exist in the provided schema."
            )

        if not extra_guidance:
            extra_guidance.append("- Fix the exact validation errors without changing the question being answered.")

        extra_guidance_text = "\n".join(extra_guidance)

        return (
            "The previous SQL candidate was invalid.\n\n"
            f"Original question:\n{question}\n\n"
            f"Schema context:\n{schema_context}\n\n"
            f"Previous SQL:\n{previous_candidate.sql}\n\n"
            f"Validation errors:\n{error_lines}\n\n"
            "Generate a corrected SQL candidate.\n"
            "Rules:\n"
            "- Return only a valid SELECT query candidate.\n"
            "- Use only the provided datasets and columns.\n"
            "- Multi-table queries are allowed when needed.\n"
            "- Qualify ambiguous columns with table names or aliases.\n"
            "- Do not invent datasets, columns, or join keys.\n"
            "- Avoid ORDER BY on select-list aliases; order by the underlying column or expression instead.\n"
            f"{extra_guidance_text}\n"
        )