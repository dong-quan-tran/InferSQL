from app.services.copilot_eval_summary import (
    CopilotEvalCaseResult,
    assert_eval_thresholds,
    build_eval_summary,
)


def test_build_eval_summary_groups_by_category() -> None:
    summary = build_eval_summary(
        [
            CopilotEvalCaseResult(id="a", category="synonym", passed=True),
            CopilotEvalCaseResult(id="b", category="synonym", passed=False),
            CopilotEvalCaseResult(id="c", category="filter", passed=True),
        ]
    )

    assert summary["total"] == 3
    assert summary["passed"] == 2
    assert summary["failed"] == 1
    assert summary["by_category"]["synonym"]["total"] == 2
    assert summary["by_category"]["synonym"]["passed"] == 1
    assert summary["by_category"]["synonym"]["failed"] == 1
    assert summary["by_category"]["filter"]["pass_rate"] == 1.0


def test_assert_eval_thresholds_accepts_passing_summary() -> None:
    summary = build_eval_summary(
        [
            CopilotEvalCaseResult(id="a", category="synonym", passed=True),
            CopilotEvalCaseResult(id="b", category="filter", passed=True),
        ]
    )

    assert_eval_thresholds(
        summary,
        minimum_overall_pass_rate=1.0,
        minimum_category_pass_rates={"synonym": 1.0, "filter": 1.0},
    )


def test_assert_eval_thresholds_raises_for_failing_category() -> None:
    summary = build_eval_summary(
        [
            CopilotEvalCaseResult(id="a", category="synonym", passed=False),
            CopilotEvalCaseResult(id="b", category="filter", passed=True),
        ]
    )

    try:
        assert_eval_thresholds(
            summary,
            minimum_category_pass_rates={"synonym": 1.0},
        )
    except AssertionError as exc:
        assert "Category 'synonym' pass rate" in str(exc)
    else:
        raise AssertionError("Expected threshold assertion to fail")