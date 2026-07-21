from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    MetricComparison,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)
from readmatch_ai.infrastructure.markdown_recommendation_quality_reporter import (
    MarkdownRecommendationQualityReporter,
)


def _report() -> RecommendationQualityReport:
    metadata = EvaluationRunMetadata(
        run_id="r1",
        generated_at="2026-01-01T00:00:00Z",
        dataset_id="demo",
        k=5,
        catalog_size=10,
        case_count=3,
        engine_names=("popularity", "semantic"),
        baseline_engine="popularity",
        ranking_strategy="weighted",
    )
    summaries = (
        RecommendationEngineQualitySummary(
            engine_name="popularity",
            metrics=(
                RecommendationMetricResult("precision_at_k", 0.2, True),
                RecommendationMetricResult("novelty_at_k", None, True),
            ),
        ),
        RecommendationEngineQualitySummary(
            engine_name="semantic",
            metrics=(
                RecommendationMetricResult("precision_at_k", 0.5, True),
                RecommendationMetricResult("novelty_at_k", 1.2, True),
            ),
        ),
    )
    comparisons = (
        MetricComparison(
            "precision_at_k", True, "semantic", {"popularity": 0.0, "semantic": 0.3}
        ),
        MetricComparison("novelty_at_k", True, "semantic", {"popularity": None, "semantic": None}),
    )
    return RecommendationQualityReport(
        format_version="1.0",
        metadata=metadata,
        engine_summaries=summaries,
        comparisons=comparisons,
        limitations=("Offline ground truth may not represent actual user intent.",),
    )


def test_render_includes_the_title() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert markdown.startswith("# Recommendation Quality Report")


def test_render_includes_run_metadata() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "r1" in markdown
    assert "demo" in markdown
    assert "weighted" in markdown


def test_render_includes_an_engine_comparison_row_per_engine() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "| popularity | 0.2000 |" in markdown
    assert "| semantic | 0.5000 |" in markdown


def test_render_formats_a_missing_metric_value_as_not_available() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "N/A" in markdown


def test_render_includes_best_engine_by_metric() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "## Best-Performing Engine by Metric" in markdown
    assert "| precision_at_k | semantic | True |" in markdown


def test_render_includes_baseline_deltas_section_with_a_disclaimer() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "## Baseline Deltas" in markdown
    assert "not a statistical significance test" in markdown


def test_render_includes_metric_interpretation_notes() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "## Metric Interpretation" in markdown
    assert "precision_at_k" in markdown


def test_render_includes_limitations() -> None:
    markdown = MarkdownRecommendationQualityReporter().render(_report())

    assert "## Limitations" in markdown
    assert "Offline ground truth may not represent actual user intent." in markdown


def test_render_is_deterministic_across_repeated_calls() -> None:
    report = _report()
    reporter = MarkdownRecommendationQualityReporter()

    assert reporter.render(report) == reporter.render(report)
