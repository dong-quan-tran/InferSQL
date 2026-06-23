from __future__ import annotations

import json

from app.schemas.copilot import CopilotSqlCandidate
from app.services.llm.prompt_assets import (
    build_few_shot_examples,
    build_synonym_guidance,
)


def build_sql_candidate_schema() -> dict:
    return CopilotSqlCandidate.model_json_schema()


def build_system_prompt() -> str:
    return (
        "You generate SQL for InferSQL.\n"
        "Rules:\n"
        "- Return JSON only.\n"
        "- Generate only SELECT queries.\n"
        "- InferSQL supports a broad but explicit analytical SQL subset over registered datasets.\n"
        "- Use multi-table SQL when needed and supported by the schema context.\n"
        "- Allowed SQL patterns include INNER JOIN, LEFT JOIN, grouped aggregates, HAVING, subqueries, UNION, and UNION ALL.\n"
        "- Only use datasets and columns present in the provided schema context.\n"
        "- Do not invent tables, columns, or join keys.\n"
        "- Qualify columns in multi-table queries when ambiguity is possible.\n"
        "- Avoid ORDER BY on select-list aliases; prefer the underlying column or expression.\n"
        "- Keep SQL compact and executable.\n"
        "- confidence must be between 0 and 1.\n"
        "- Map business synonyms to actual schema names when supported by the schema context.\n"
        "- If a user term does not exactly match a column name, prefer the closest schema-supported canonical column.\n"
        "- Record important term mappings or interpretation choices in assumptions.\n"
        "- If the request cannot be answered from the provided schema context, return the closest valid SQL you can support and explain the limitation in assumptions.\n"
    )


def build_user_prompt(question: str, schema_context: str) -> str:
    schema = build_sql_candidate_schema()
    synonym_guidance = build_synonym_guidance()
    few_shot_examples = build_few_shot_examples()

    return (
        f"Schema context:\n{schema_context}\n\n"
        f"{synonym_guidance}\n\n"
        f"{few_shot_examples}\n\n"
        "Use the examples as patterns, not as fixed dataset requirements.\n\n"
        f"Question:\n{question}\n\n"
        "Return a JSON object matching this schema exactly:\n"
        f"{json.dumps(schema)}"
    )