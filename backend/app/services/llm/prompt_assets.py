from __future__ import annotations

import json


CANONICAL_SYNONYM_RULES: dict[str, str] = {
    "ticker": "symbol",
    "tickers": "symbol",
    "stock symbol": "symbol",
    "stock symbols": "symbol",
    "price": "close",
    "stock price": "close",
    "share price": "close",
    "closing price": "close",
    "close price": "close",
    "market cap": "market_cap",
    "market capitalization": "market_cap",
}


FEW_SHOT_EXAMPLES: list[dict] = [
    {
        "question": "Show one stock symbol",
        "response": {
            "sql": "SELECT symbol FROM prices LIMIT 1",
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol"],
            "confidence": 0.95,
        },
    },
    {
        "question": "Show stock symbols and closing prices",
        "response": {
            "sql": "SELECT symbol, close FROM prices LIMIT 5",
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.96,
        },
    },
    {
        "question": "Show the closing price for MSFT",
        "response": {
            "sql": "SELECT symbol, close FROM prices WHERE symbol = 'MSFT'",
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.94,
        },
    },
    {
        "question": "Show stocks with close greater than 200",
        "response": {
            "sql": "SELECT symbol, close FROM prices WHERE close > 200",
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.93,
        },
    },
    {
        "question": "Show ticker and close",
        "response": {
            "sql": "SELECT symbol, close FROM prices",
            "assumptions": ["Mapped ticker to symbol based on schema context."],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.84,
        },
    },
    {
        "question": "Show stock price for AAPL",
        "response": {
            "sql": "SELECT close FROM prices WHERE symbol = 'AAPL'",
            "assumptions": ["Mapped stock price to close based on schema context."],
            "referenced_tables": ["prices"],
            "referenced_columns": ["close", "symbol"],
            "confidence": 0.85,
        },
    },
    {
        "question": "Show market cap for MSFT",
        "response": {
            "sql": "SELECT market_cap FROM fundamentals WHERE symbol = 'MSFT'",
            "assumptions": ["Mapped market cap to market_cap based on schema context."],
            "referenced_tables": ["fundamentals"],
            "referenced_columns": ["market_cap", "symbol"],
            "confidence": 0.83,
        },
    },
]


def build_synonym_guidance() -> str:
    lines = ["Canonical business-term mappings:"]
    for source, target in sorted(CANONICAL_SYNONYM_RULES.items()):
        lines.append(f"- {source} -> {target}")
    return "\n".join(lines)


def build_few_shot_examples() -> str:
    lines = ["Examples:"]
    for idx, example in enumerate(FEW_SHOT_EXAMPLES, start=1):
        lines.append(f"Example {idx} question:")
        lines.append(example["question"])
        lines.append("Example output JSON:")
        lines.append(json.dumps(example["response"]))
        lines.append("")
    return "\n".join(lines).strip()