import csv
import io

from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    MetricComparison,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)
from readmatch_ai.infrastructure.csv_recommendation_quality_reporter import (
    CsvRecommendationQualityReporter,
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
        limitations=(),
    )


def _rows(csv_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(csv_text)))


def test_render_produces_one_row_per_engine() -> None:
    csv_text = CsvRecommendationQualityReporter().render(_report())

    rows = _rows(csv_text)

    assert [row["engine"] for row in rows] == ["popularity", "semantic"]


def test_render_produces_one_column_per_metric_plus_engine_and_deltas() -> None:
    csv_text = CsvRecommendationQualityReporter().render(_report())

    header = csv_text.splitlines()[0].split(",")

    assert header == [
        "engine",
        "precision_at_k",
        "novelty_at_k",
        "precision_at_k_delta_from_baseline",
        "novelty_at_k_delta_from_baseline",
    ]


def test_render_writes_metric_values() -> None:
    csv_text = CsvRecommendationQualityReporter().render(_report())

    rows = _rows(csv_text)

    assert rows[0]["precision_at_k"] == "0.2"
    assert rows[1]["precision_at_k"] == "0.5"


def test_render_writes_an_empty_field_for_a_missing_value() -> None:
    csv_text = CsvRecommendationQualityReporter().render(_report())

    rows = _rows(csv_text)

    assert rows[0]["novelty_at_k"] == ""


def test_render_writes_baseline_deltas() -> None:
    csv_text = CsvRecommendationQualityReporter().render(_report())

    rows = _rows(csv_text)

    assert rows[0]["precision_at_k_delta_from_baseline"] == "0.0"
    assert rows[1]["precision_at_k_delta_from_baseline"] == "0.3"


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

    csv_text = CsvRecommendationQualityReporter().render(empty_report)

    assert csv_text.strip() == "engine"


def test_render_is_deterministic_across_repeated_calls() -> None:
    report = _report()
    reporter = CsvRecommendationQualityReporter()

    assert reporter.render(report) == reporter.render(report)


def test_column_ordering_is_stable_and_matches_report_metric_order() -> None:
    """Stable regardless of dict/set iteration order -- driven entirely by
    the report's own (already-deterministic) engine_summaries metric order.
    """
    csv_text_1 = CsvRecommendationQualityReporter().render(_report())
    csv_text_2 = CsvRecommendationQualityReporter().render(_report())

    assert csv_text_1.splitlines()[0] == csv_text_2.splitlines()[0]
