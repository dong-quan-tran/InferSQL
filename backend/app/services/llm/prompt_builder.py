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
        "- Do not return markdown fences.\n"
        "- Do not return explanatory prose outside the JSON object.\n"
        "- Generate only SELECT queries.\n"
        "- InferSQL supports a broad but explicit analytical SQL subset over registered datasets.\n"
        "- Use only datasets and columns present in the provided schema context.\n"
        "- Do not invent tables, columns, aliases, filters, or join keys.\n"
        "- Keep SQL compact and executable.\n"
        "- confidence must be between 0 and 1.\n"
        "- referenced_tables must list every dataset used by the SQL.\n"
        "- referenced_columns must list the schema columns referenced by the SQL.\n"
        "- assumptions must record important mappings, repairs, ambiguities, or limitations.\n"
        "\n"
        "Supported SQL patterns:\n"
        "- Single-table SELECT queries.\n"
        "- Multi-table queries when supported by the schema context.\n"
        "- INNER JOIN and LEFT JOIN.\n"
        "- GROUP BY and HAVING.\n"
        "- COUNT, SUM, AVG, MIN, and MAX.\n"
        "- WHERE filters, including IN subqueries.\n"
        "- Scalar subqueries.\n"
        "- UNION and UNION ALL when column shapes are compatible.\n"
        "\n"
        "Join and qualification rules:\n"
        "- Use multi-table SQL only when it is necessary to answer the question.\n"
        "- Prefer explicit join conditions using keys that are clearly present in the schema context.\n"
        "- Qualify columns in multi-table queries whenever ambiguity is possible.\n"
        "- Prefer explicit column lists over SELECT * unless the user clearly asks for all columns.\n"
        "- Avoid ORDER BY on select-list aliases; prefer the underlying column or expression.\n"
        "\n"
        "Schema grounding rules:\n"
        "- Map business synonyms to actual schema names when supported by the schema context.\n"
        "- If a user term does not exactly match a column name, prefer the closest schema-supported canonical column.\n"
        "- If a user asks for 'ticker' and the schema provides 'symbol', use 'symbol' and record the mapping in assumptions.\n"
        "- If a user asks for 'price' and the schema provides 'close', use 'close' and record the mapping in assumptions.\n"
        "- If the schema does not support the exact request, return the closest valid SQL you can support and explain the limitation in assumptions.\n"
        "\n"
        "Ambiguity rules:\n"
        "- If the question is ambiguous, choose the most reasonable schema-supported interpretation.\n"
        "- If words like 'latest', 'best', or 'top' cannot be grounded by available columns, return a conservative valid query and explain the limitation in assumptions.\n"
        "- Do not fabricate time logic, ranking metrics, or business definitions that are not supported by the schema context.\n"
        "\n"
        "Output format rules:\n"
        "- Return exactly one JSON object matching the CopilotSqlCandidate schema.\n"
        "- Use double-quoted JSON.\n"
        "- Do not add extra keys.\n"
        "- Ensure sql is a string, assumptions is a list of strings, referenced_tables is a list of strings, referenced_columns is a list of strings, and confidence is a number.\n"
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
        f"User question:\n{question}\n\n"
        "Instructions:\n"
        "- Use only datasets and columns that appear in the schema context.\n"
        "- Prefer the smallest valid query that answers the question.\n"
        "- Use joins only when they are necessary to answer the question.\n"
        "- When combining datasets, use explicit join conditions grounded in the schema context.\n"
        "- For grouped metrics, use GROUP BY and HAVING when appropriate.\n"
        "- For nested filtering logic, subqueries are allowed when needed.\n"
        "- If the user uses a synonym rather than an exact schema name, map it to the closest supported schema term and record that choice in assumptions.\n"
        "- If the request is partially unsupported by the schema, return the closest valid SQL and explain the limitation in assumptions.\n"
        "- If the request is ambiguous, choose a conservative schema-supported interpretation and explain it in assumptions.\n\n"
        "Return a JSON object matching this schema exactly:\n"
        f"{json.dumps(schema)}"
    )