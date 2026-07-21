import pytest

from readmatch_ai.domain.quality_regression import (
    RegressionThreshold,
    check_recommendation_quality_regressions,
)
from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)


def _metric(name: str, value: float | None) -> RecommendationMetricResult:
    return RecommendationMetricResult(name=name, value=value, higher_is_better=True)


def _report(
    engine_values: dict[str, dict[str, float | None]], baseline_engine: str = "popularity"
) -> RecommendationQualityReport:
    summaries = tuple(
        RecommendationEngineQualitySummary(
            engine_name=engine_name,
            metrics=tuple(_metric(name, value) for name, value in metrics.items()),
        )
        for engine_name, metrics in engine_values.items()
    )
    metadata = EvaluationRunMetadata(
        run_id="r1",
        generated_at="2026-01-01T00:00:00Z",
        dataset_id="demo",
        k=5,
        catalog_size=10,
        case_count=3,
        engine_names=tuple(engine_values),
        baseline_engine=baseline_engine,
    )
    return RecommendationQualityReport(
        format_version="1.0",
        metadata=metadata,
        engine_summaries=summaries,
        comparisons=(),
        limitations=(),
    )


def test_regression_threshold_requires_at_least_one_bound() -> None:
    with pytest.raises(ValueError, match="minimum_value"):
        RegressionThreshold("popularity", "precision_at_k")


def test_empty_thresholds_always_pass() -> None:
    report = _report({"popularity": {"precision_at_k": 0.1}})

    result = check_recommendation_quality_regressions(report, [])

    assert result.passed is True
    assert result.failures == ()


def test_minimum_value_threshold_passes_when_satisfied() -> None:
    report = _report({"popularity": {"precision_at_k": 0.5}})
    threshold = RegressionThreshold("popularity", "precision_at_k", minimum_value=0.3)

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is True


def test_minimum_value_threshold_fails_when_below_floor() -> None:
    report = _report({"popularity": {"precision_at_k": 0.1}})
    threshold = RegressionThreshold("popularity", "precision_at_k", minimum_value=0.3)

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert failure.engine_name == "popularity"
    assert failure.metric_name == "precision_at_k"
    assert "0.1" in failure.message
    assert "0.3" in failure.message


def test_max_regression_from_baseline_passes_within_tolerance() -> None:
    report = _report(
        {"popularity": {"precision_at_k": 0.5}, "hybrid": {"precision_at_k": 0.45}}
    )
    threshold = RegressionThreshold(
        "hybrid", "precision_at_k", max_regression_from_baseline=0.1
    )

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is True


def test_max_regression_from_baseline_fails_beyond_tolerance() -> None:
    report = _report(
        {"popularity": {"precision_at_k": 0.5}, "hybrid": {"precision_at_k": 0.2}}
    )
    threshold = RegressionThreshold(
        "hybrid", "precision_at_k", max_regression_from_baseline=0.1
    )

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert "hybrid" in result.failures[0].message
    assert "baseline" in result.failures[0].message


def test_allowed_tolerance_is_an_inclusive_floor() -> None:
    """Exactly at the tolerance boundary must pass, not fail."""
    report = _report(
        {"popularity": {"precision_at_k": 0.5}, "hybrid": {"precision_at_k": 0.4}}
    )
    threshold = RegressionThreshold(
        "hybrid", "precision_at_k", max_regression_from_baseline=0.1
    )

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is True


def test_both_bounds_can_be_checked_together() -> None:
    report = _report({"popularity": {"precision_at_k": 0.5}, "hybrid": {"precision_at_k": 0.05}})
    threshold = RegressionThreshold(
        "hybrid", "precision_at_k", minimum_value=0.1, max_regression_from_baseline=0.6
    )

    result = check_recommendation_quality_regressions(report, [threshold])

    # Fails the absolute floor even though it's within the baseline tolerance.
    assert result.passed is False
    assert len(result.failures) == 1


def test_unevaluated_engine_produces_a_clear_failure() -> None:
    report = _report({"popularity": {"precision_at_k": 0.5}})
    threshold = RegressionThreshold("nonexistent", "precision_at_k", minimum_value=0.1)

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert "nonexistent" in result.failures[0].message
    assert "not evaluated" in result.failures[0].message


def test_unknown_metric_produces_a_clear_failure() -> None:
    report = _report({"popularity": {"precision_at_k": 0.5}})
    threshold = RegressionThreshold("popularity", "unknown_metric", minimum_value=0.1)

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert "unknown_metric" in result.failures[0].message


def test_missing_metric_value_produces_a_clear_failure_not_a_silent_pass() -> None:
    report = _report({"popularity": {"novelty_at_k": None}})
    threshold = RegressionThreshold("popularity", "novelty_at_k", minimum_value=0.1)

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert "insufficient evidence" in result.failures[0].message


def test_missing_baseline_value_produces_a_clear_failure_for_regression_tolerance() -> None:
    report = _report({"popularity": {"precision_at_k": None}, "hybrid": {"precision_at_k": 0.5}})
    threshold = RegressionThreshold(
        "hybrid", "precision_at_k", max_regression_from_baseline=0.1
    )

    result = check_recommendation_quality_regressions(report, [threshold])

    assert result.passed is False
    assert "baseline" in result.failures[0].message


def test_all_failures_are_reported_not_just_the_first() -> None:
    report = _report({"popularity": {"precision_at_k": 0.1, "recall_at_k": 0.1}})
    thresholds = [
        RegressionThreshold("popularity", "precision_at_k", minimum_value=0.5),
        RegressionThreshold("popularity", "recall_at_k", minimum_value=0.5),
    ]

    result = check_recommendation_quality_regressions(report, thresholds)

    assert len(result.failures) == 2


def test_check_is_deterministic_across_repeated_calls() -> None:
    report = _report({"popularity": {"precision_at_k": 0.1}})
    threshold = RegressionThreshold("popularity", "precision_at_k", minimum_value=0.5)

    first = check_recommendation_quality_regressions(report, [threshold])
    second = check_recommendation_quality_regressions(report, [threshold])

    assert first == second
