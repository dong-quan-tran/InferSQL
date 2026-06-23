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
    {
        "question": "Show symbols and market cap by joining prices with fundamentals",
        "response": {
            "sql": (
                "SELECT p.symbol, f.market_cap "
                "FROM prices AS p "
                "JOIN fundamentals AS f ON p.symbol = f.symbol"
            ),
            "assumptions": ["Used symbol as the join key because it exists in both datasets."],
            "referenced_tables": ["prices", "fundamentals"],
            "referenced_columns": ["symbol", "market_cap"],
            "confidence": 0.88,
        },
    },
    {
        "question": "List all price symbols and include market cap if available",
        "response": {
            "sql": (
                "SELECT p.symbol, p.close, f.market_cap "
                "FROM prices AS p "
                "LEFT JOIN fundamentals AS f ON p.symbol = f.symbol"
            ),
            "assumptions": ["Used LEFT JOIN so symbols from prices remain even when fundamentals are missing."],
            "referenced_tables": ["prices", "fundamentals"],
            "referenced_columns": ["symbol", "close", "market_cap"],
            "confidence": 0.89,
        },
    },
    {
        "question": "Show symbols with more than 10 rows and average close above 100",
        "response": {
            "sql": (
                "SELECT symbol, COUNT(*) AS row_count, AVG(close) AS avg_close "
                "FROM prices "
                "GROUP BY symbol "
                "HAVING COUNT(*) > 10 AND AVG(close) > 100"
            ),
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.9,
        },
    },
    {
        "question": "Show rows for symbols that exist in fundamentals",
        "response": {
            "sql": (
                "SELECT symbol, close "
                "FROM prices "
                "WHERE symbol IN (SELECT symbol FROM fundamentals)"
            ),
            "assumptions": [],
            "referenced_tables": ["prices", "fundamentals"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.88,
        },
    },
    {
        "question": "For each symbol, show its average close and the overall average close",
        "response": {
            "sql": (
                "SELECT symbol, AVG(close) AS symbol_avg_close, "
                "(SELECT AVG(close) FROM prices) AS overall_avg_close "
                "FROM prices "
                "GROUP BY symbol"
            ),
            "assumptions": [],
            "referenced_tables": ["prices"],
            "referenced_columns": ["symbol", "close"],
            "confidence": 0.87,
        },
    },
    {
        "question": "Combine prices and prices_nulls into one result with all rows",
        "response": {
            "sql": (
                "SELECT symbol, close, ts FROM prices "
                "UNION ALL "
                "SELECT symbol, close, ts FROM prices_nulls"
            ),
            "assumptions": ["Used UNION ALL to preserve all rows from both datasets."],
            "referenced_tables": ["prices", "prices_nulls"],
            "referenced_columns": ["symbol", "close", "ts"],
            "confidence": 0.86,
        },
    },
]


def canonical_aliases_by_column() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for source, target in CANONICAL_SYNONYM_RULES.items():
        aliases.setdefault(target, []).append(source)

    for column_name in aliases:
        aliases[column_name] = sorted(aliases[column_name])

    return aliases


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