from app.services.llm.prompt_assets import (
    CANONICAL_SYNONYM_RULES,
    build_few_shot_examples,
    build_synonym_guidance,
)


def test_synonym_rules_include_expected_mappings() -> None:
    assert CANONICAL_SYNONYM_RULES["ticker"] == "symbol"
    assert CANONICAL_SYNONYM_RULES["stock price"] == "close"
    assert CANONICAL_SYNONYM_RULES["market cap"] == "market_cap"


def test_build_synonym_guidance_contains_expected_lines() -> None:
    guidance = build_synonym_guidance()

    assert "Canonical business-term mappings:" in guidance
    assert "- ticker -> symbol" in guidance
    assert "- stock price -> close" in guidance
    assert "- market cap -> market_cap" in guidance


def test_build_few_shot_examples_contains_synonym_examples() -> None:
    examples = build_few_shot_examples()

    assert "Show ticker and close" in examples
    assert "Show stock price for AAPL" in examples
    assert "Show market cap for MSFT" in examples