import pytest

from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)


def _metric(name: str, value: float | None = 1.0) -> RecommendationMetricResult:
    return RecommendationMetricResult(name=name, value=value, higher_is_better=True)


def _summary(engine_name: str) -> RecommendationEngineQualitySummary:
    return RecommendationEngineQualitySummary(
        engine_name=engine_name, metrics=(_metric("precision_at_k"),)
    )


def _metadata() -> EvaluationRunMetadata:
    return EvaluationRunMetadata(
        run_id="r1",
        generated_at="2026-01-01T00:00:00Z",
        dataset_id="demo",
        k=5,
        catalog_size=10,
        case_count=3,
        engine_names=("popularity",),
        baseline_engine="popularity",
    )


def test_engine_quality_summary_metric_returns_the_matching_result() -> None:
    summary = _summary("popularity")

    result = summary.metric("precision_at_k")

    assert result.name == "precision_at_k"
    assert result.value == 1.0


def test_engine_quality_summary_metric_raises_for_an_unknown_metric() -> None:
    summary = _summary("popularity")

    with pytest.raises(KeyError):
        summary.metric("unknown_metric")


def test_report_summary_for_returns_the_matching_engine_summary() -> None:
    report = RecommendationQualityReport(
        format_version="1.0",
        metadata=_metadata(),
        engine_summaries=(_summary("popularity"), _summary("semantic")),
        comparisons=(),
        limitations=(),
    )

    assert report.summary_for("semantic").engine_name == "semantic"


def test_report_summary_for_raises_for_an_unknown_engine() -> None:
    report = RecommendationQualityReport(
        format_version="1.0",
        metadata=_metadata(),
        engine_summaries=(_summary("popularity"),),
        comparisons=(),
        limitations=(),
    )

    with pytest.raises(KeyError):
        report.summary_for("unknown_engine")


def test_evaluation_run_metadata_defaults_optional_fields_to_none() -> None:
    metadata = _metadata()

    assert metadata.user_count is None
    assert metadata.ranking_strategy is None
    assert metadata.reranking_policies is None
    assert metadata.embedding_provider is None
    assert metadata.embedding_model is None
    assert metadata.embedding_dimensions is None
    assert metadata.als_factors is None
    assert metadata.als_iterations is None
    assert metadata.project_version is None
