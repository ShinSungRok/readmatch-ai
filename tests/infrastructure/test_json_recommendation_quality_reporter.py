import json

from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    MetricComparison,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)
from readmatch_ai.infrastructure.json_recommendation_quality_reporter import (
    JsonRecommendationQualityReporter,
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
        limitations=("Limitation one.",),
    )


def test_render_produces_valid_json() -> None:
    json_text = JsonRecommendationQualityReporter().render(_report())

    document = json.loads(json_text)

    assert document["format_version"] == "1.0"


def test_render_includes_metadata_fields() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    metadata = document["metadata"]
    assert metadata["run_id"] == "r1"
    assert metadata["dataset_id"] == "demo"
    assert metadata["k"] == 5
    assert metadata["engine_names"] == ["popularity", "semantic"]
    assert metadata["baseline_engine"] == "popularity"


def test_render_includes_one_engine_summary_per_engine_in_order() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    assert [s["engine_name"] for s in document["engine_summaries"]] == ["popularity", "semantic"]


def test_render_writes_metric_values() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    popularity_metrics = {m["name"]: m["value"] for m in document["engine_summaries"][0]["metrics"]}
    assert popularity_metrics["precision_at_k"] == 0.2


def test_render_writes_null_for_a_missing_metric_value() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    popularity_metrics = {m["name"]: m["value"] for m in document["engine_summaries"][0]["metrics"]}
    assert popularity_metrics["novelty_at_k"] is None


def test_render_writes_comparisons_with_deltas() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    precision_comparison = next(
        c for c in document["comparisons"] if c["metric_name"] == "precision_at_k"
    )
    assert precision_comparison["best_engine"] == "semantic"
    assert precision_comparison["deltas_from_baseline"] == {"popularity": 0.0, "semantic": 0.3}


def test_render_writes_null_deltas_when_no_value_is_available() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    novelty_comparison = next(
        c for c in document["comparisons"] if c["metric_name"] == "novelty_at_k"
    )
    assert novelty_comparison["deltas_from_baseline"] == {"popularity": None, "semantic": None}


def test_render_includes_limitations() -> None:
    document = json.loads(JsonRecommendationQualityReporter().render(_report()))

    assert document["limitations"] == ["Limitation one."]


def test_render_handles_a_report_with_no_engines() -> None:
    empty_report = RecommendationQualityReport(
        format_version="1.0",
        metadata=EvaluationRunMetadata(
            run_id="r1",
            generated_at="2026-01-01T00:00:00Z",
            dataset_id="demo",
            k=5,
            catalog_size=10,
            case_count=0,
            engine_names=(),
            baseline_engine="popularity",
        ),
        engine_summaries=(),
        comparisons=(),
        limitations=(),
    )

    document = json.loads(JsonRecommendationQualityReporter().render(empty_report))

    assert document["engine_summaries"] == []
    assert document["comparisons"] == []


def test_render_is_deterministic_across_repeated_calls() -> None:
    report = _report()
    reporter = JsonRecommendationQualityReporter()

    assert reporter.render(report) == reporter.render(report)
