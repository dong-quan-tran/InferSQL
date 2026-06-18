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
        "- Prefer a single-table query.\n"
        "- Only use datasets and columns present in the provided schema context.\n"
        "- Do not invent tables or columns.\n"
        "- Keep SQL compact and executable.\n"
        "- confidence must be between 0 and 1.\n"
        "- Map business synonyms to actual schema names when supported by the schema context.\n"
        "- If a user term does not exactly match a column name, prefer the closest schema-supported canonical column.\n"
        "- Record important term mappings in assumptions.\n"
    )


def build_user_prompt(question: str, schema_context: str) -> str:
    schema = build_sql_candidate_schema()
    synonym_guidance = build_synonym_guidance()
    few_shot_examples = build_few_shot_examples()

    return (
        f"Schema context:\n{schema_context}\n\n"
        f"{synonym_guidance}\n\n"
        f"{few_shot_examples}\n\n"
        f"Question:\n{question}\n\n"
        "Return a JSON object matching this schema exactly:\n"
        f"{json.dumps(schema)}"
    )