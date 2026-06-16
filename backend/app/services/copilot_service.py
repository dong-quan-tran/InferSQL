from __future__ import annotations

from app.core.catalog.registry import DatasetRegistry
from app.schemas.copilot import CopilotQueryResponse
from app.services.llm.base import LLMProvider
from app.services.query_service import QueryService


class CopilotService:
    def __init__(
        self,
        dataset_registry: DatasetRegistry,
        query_service: QueryService,
        llm_provider: LLMProvider,
    ) -> None:
        self.dataset_registry = dataset_registry
        self.query_service = query_service
        self.llm_provider = llm_provider

    def query(
        self,
        question: str,
        execute: bool = False,
        request_id: str | None = None,
    ) -> CopilotQueryResponse:
        schema_context = self._build_schema_context()
        candidate = self.llm_provider.generate_sql_candidate(
            question=question,
            schema_context=schema_context,
        )

        validation = self.query_service.validate(
            sql=candidate.sql,
            request_id=request_id,
            debug=False,
        )

        execution = None
        if execute and validation["is_valid"]:
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
        )

    def _build_schema_context(self) -> str:
        parts: list[str] = []

        for table_name in self.dataset_registry.list_tables():
            description = self.dataset_registry.describe_table(table_name)
            columns = ", ".join(
                f"{name}:{dtype}"
                for name, dtype in description["types"].items()
            )
            parts.append(f"- {table_name}({columns})")

        return "\n".join(parts)