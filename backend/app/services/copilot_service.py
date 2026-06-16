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

    def query(
        self,
        question: str,
        execute: bool = False,
        request_id: str | None = None,
    ) -> CopilotQueryResponse:
        schema_context = self._build_schema_context()
        retry_history: list[CopilotRetryStep] = []

        candidate = self.llm_provider.generate_sql_candidate(
            question=question,
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

    def _build_schema_context(self) -> str:
        return self.schema_context_builder.build()

    def _build_repair_prompt(
        self,
        question: str,
        schema_context: str,
        previous_candidate: CopilotSqlCandidate,
        validation: CopilotValidationResult,
    ) -> str:
        error_lines = "\n".join(f"- {error}" for error in validation.errors) or "- Unknown validation error"

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
            "- Keep the query single-table unless explicitly supported.\n"
            "- Fix the exact validation errors.\n"
        )