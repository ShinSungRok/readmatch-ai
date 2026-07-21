import pytest

from readmatch_ai.application.generate_recommendation_quality_report_use_case import (
    GenerateRecommendationQualityReportUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.quality_report import QualityReportRunConfig
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


def _book(book_id: BookId) -> Book:
    return Book(
        id=book_id,
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Title"),
        author=Author("Author"),
        category=Category("Category"),
    )


class _FixedScoreEngine(RecommendationEngine):
    """Always recommends `hit` (relevant) at a fixed score."""

    def __init__(self, hit: BookId, score: float) -> None:
        self._hit = hit
        self._score = score

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        item = RecommendationItem(book=_book(self._hit), score=self._score, source="fake")
        return RecommendationResult(recommendation=Recommendation(items=[item]))


def _dataset(hit: BookId) -> EvaluationDataset:
    return EvaluationDataset(
        cases=(EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset({hit})),)
    )


def _config(**overrides: object) -> QualityReportRunConfig:
    defaults: dict[str, object] = dict(
        run_id="r1",
        generated_at="2026-01-01T00:00:00Z",
        dataset_id="demo",
        baseline_engine="popularity",
        catalog_size=10,
    )
    defaults.update(overrides)
    return QualityReportRunConfig(**defaults)  # type: ignore[arg-type]


def test_execute_raises_when_baseline_engine_is_not_among_the_evaluated_engines() -> None:
    hit = BookId.generate()
    engines = [("popularity", _FixedScoreEngine(hit, 1.0))]

    with pytest.raises(ValueError, match="baseline_engine"):
        GenerateRecommendationQualityReportUseCase().execute(
            engines, _dataset(hit), k=1, config=_config(baseline_engine="semantic")
        )


def test_execute_produces_one_summary_per_engine_in_input_order() -> None:
    hit = BookId.generate()
    engines = [
        ("popularity", _FixedScoreEngine(hit, 1.0)),
        ("semantic", _FixedScoreEngine(hit, 1.0)),
    ]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, _dataset(hit), k=1, config=_config()
    )

    assert [s.engine_name for s in report.engine_summaries] == ["popularity", "semantic"]


def test_execute_populates_metadata_from_config_and_inputs() -> None:
    hit = BookId.generate()
    engines = [("popularity", _FixedScoreEngine(hit, 1.0))]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines,
        _dataset(hit),
        k=3,
        config=_config(ranking_strategy="weighted", project_version="1.2.3"),
    )

    assert report.metadata.run_id == "r1"
    assert report.metadata.generated_at == "2026-01-01T00:00:00Z"
    assert report.metadata.dataset_id == "demo"
    assert report.metadata.k == 3
    assert report.metadata.catalog_size == 10
    assert report.metadata.case_count == 1
    assert report.metadata.engine_names == ("popularity",)
    assert report.metadata.baseline_engine == "popularity"
    assert report.metadata.ranking_strategy == "weighted"
    assert report.metadata.project_version == "1.2.3"
    assert report.format_version == "1.0"
    assert len(report.limitations) > 0


def test_best_engine_selection_picks_the_higher_value() -> None:
    hit = BookId.generate()
    dataset = EvaluationDataset(
        cases=(
            EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset({hit})),
            EvaluationCase(
                book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()})
            ),
        )
    )

    class _OnlyPopularityHits(RecommendationEngine):
        def recommend(self, query: RecommendationQuery) -> RecommendationResult:
            return RecommendationResult(
                recommendation=Recommendation(items=[RecommendationItem(_book(hit), 1.0, "f")])
            )

    class _NeverHits(RecommendationEngine):
        def recommend(self, query: RecommendationQuery) -> RecommendationResult:
            return RecommendationResult(
                recommendation=Recommendation(
                    items=[RecommendationItem(_book(BookId.generate()), 1.0, "f")]
                )
            )

    engines = [("popularity", _OnlyPopularityHits()), ("semantic", _NeverHits())]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, dataset, k=1, config=_config()
    )

    precision_comparison = next(c for c in report.comparisons if c.metric_name == "precision_at_k")
    assert precision_comparison.best_engine == "popularity"


def test_best_engine_selection_breaks_ties_by_input_order() -> None:
    hit = BookId.generate()
    engines = [
        ("popularity", _FixedScoreEngine(hit, 1.0)),
        ("semantic", _FixedScoreEngine(hit, 1.0)),
        ("als", _FixedScoreEngine(hit, 1.0)),
    ]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, _dataset(hit), k=1, config=_config()
    )

    # All three engines tie on every metric (identical recommendations) --
    # the first-listed engine, "popularity", must always win.
    for comparison in report.comparisons:
        if comparison.best_engine is not None:
            assert comparison.best_engine == "popularity"


def test_baseline_deltas_are_zero_for_the_baseline_engine_itself() -> None:
    hit = BookId.generate()
    engines = [("popularity", _FixedScoreEngine(hit, 1.0))]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, _dataset(hit), k=1, config=_config()
    )

    for comparison in report.comparisons:
        if comparison.deltas_from_baseline["popularity"] is not None:
            assert comparison.deltas_from_baseline["popularity"] == pytest.approx(0.0)


def test_baseline_deltas_reflect_the_difference_from_baseline() -> None:
    hit = BookId.generate()
    miss = BookId.generate()
    dataset = _dataset(hit)
    engines = [
        ("popularity", _FixedScoreEngine(miss, 1.0)),  # never hits -> precision 0
        ("semantic", _FixedScoreEngine(hit, 1.0)),  # always hits -> precision 1
    ]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, dataset, k=1, config=_config()
    )

    precision_comparison = next(c for c in report.comparisons if c.metric_name == "precision_at_k")
    assert precision_comparison.deltas_from_baseline["semantic"] == pytest.approx(1.0)


def test_execute_computes_coverage_and_novelty_when_config_supplies_evidence() -> None:
    hit = BookId.generate()
    engines = [("popularity", _FixedScoreEngine(hit, 1.0))]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines,
        _dataset(hit),
        k=1,
        config=_config(catalog_size=4, popularity_by_book_id={hit: 2}),
    )

    summary = report.summary_for("popularity")
    assert summary.metric("coverage").value == pytest.approx(0.25)
    assert summary.metric("novelty_at_k").value == pytest.approx(0.0)


def test_execute_is_deterministic_across_repeated_calls() -> None:
    hit = BookId.generate()
    engines = [("popularity", _FixedScoreEngine(hit, 1.0))]
    dataset = _dataset(hit)
    config = _config()

    use_case = GenerateRecommendationQualityReportUseCase()
    first = use_case.execute(engines, dataset, k=1, config=config)
    second = use_case.execute(engines, dataset, k=1, config=config)

    assert first == second
