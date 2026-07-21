import pytest

from readmatch_ai.application.evaluate_recommendation_engine_use_case import (
    EvaluateRecommendationEngineUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


def _book(book_id: BookId) -> Book:
    # A fixed valid ISBN is fine here: these Books are never persisted
    # through a repository, so ISBN uniqueness doesn't matter.
    return Book(
        id=book_id,
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Title"),
        author=Author("Author"),
        category=Category("Category"),
    )


class _FakeRecommendationEngine(RecommendationEngine):
    """Returns a fixed ranked list of book ids for every query, regardless of book_id."""

    def __init__(self, ranked_book_ids: list[BookId]) -> None:
        self._items = [
            RecommendationItem(book=_book(book_id), score=1.0, source="fake")
            for book_id in ranked_book_ids
        ]
        self.received_queries: list[RecommendationQuery] = []

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_queries.append(query)
        return RecommendationResult(recommendation=Recommendation(items=self._items[: query.limit]))


def test_execute_queries_the_engine_per_case_with_k_as_limit() -> None:
    source_a = BookId.generate()
    source_b = BookId.generate()
    engine = _FakeRecommendationEngine([BookId.generate()])
    dataset = EvaluationDataset(
        cases=(
            EvaluationCase(book_id=source_a, relevant_book_ids=frozenset({BookId.generate()})),
            EvaluationCase(book_id=source_b, relevant_book_ids=frozenset({BookId.generate()})),
        )
    )

    EvaluateRecommendationEngineUseCase().execute(engine, "fake", dataset, k=3)

    assert [query.book_id for query in engine.received_queries] == [source_a, source_b]
    assert all(query.limit == 3 for query in engine.received_queries)


def test_execute_queries_the_engine_with_user_id_for_a_user_based_case() -> None:
    """A collaborative-filtering (e.g. ALS) case is keyed by user_id, not book_id."""
    user_id = UserId.generate()
    engine = _FakeRecommendationEngine([BookId.generate()])
    dataset = EvaluationDataset(
        cases=(EvaluationCase(user_id=user_id, relevant_book_ids=frozenset({BookId.generate()})),)
    )

    EvaluateRecommendationEngineUseCase().execute(engine, "fake", dataset, k=5)

    assert engine.received_queries[0].user_id == user_id
    assert engine.received_queries[0].book_id is None


def test_execute_aggregates_metrics_as_the_mean_across_cases() -> None:
    hit, miss = BookId.generate(), BookId.generate()
    # Case 1: the engine's only recommendation is relevant -> perfect scores.
    # Case 2: the engine's only recommendation is not relevant -> zero scores.
    hit_case = EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset({hit}))
    miss_case = EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset({miss}))
    dataset = EvaluationDataset(cases=(hit_case, miss_case))

    class _PerCaseEngine(RecommendationEngine):
        def recommend(self, query: RecommendationQuery) -> RecommendationResult:
            book_id = hit if query.book_id == hit_case.book_id else BookId.generate()
            item = RecommendationItem(book=_book(book_id), score=1.0, source="fake")
            return RecommendationResult(recommendation=Recommendation(items=[item]))

    result = EvaluateRecommendationEngineUseCase().execute(_PerCaseEngine(), "fake", dataset, k=1)

    assert result.engine_name == "fake"
    assert result.k == 1
    assert result.case_count == 2
    assert result.precision_at_k == pytest.approx(0.5)
    assert result.recall_at_k == pytest.approx(0.5)
    assert result.map_at_k == pytest.approx(0.5)
    assert result.ndcg_at_k == pytest.approx(0.5)
    assert result.hit_rate_at_k == pytest.approx(0.5)
    # Every case's single recommendation is the only item in its list, so
    # each case is trivially "fully diverse" (1 distinct category / 1 item).
    assert result.diversity_at_k == pytest.approx(1.0)


def test_execute_returns_zero_scores_when_no_recommendation_is_relevant() -> None:
    case = EvaluationCase(
        book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()})
    )
    dataset = EvaluationDataset(cases=(case,))
    engine = _FakeRecommendationEngine([BookId.generate(), BookId.generate()])

    result = EvaluateRecommendationEngineUseCase().execute(engine, "fake", dataset, k=2)

    assert result.precision_at_k == 0.0
    assert result.recall_at_k == 0.0
    assert result.map_at_k == 0.0
    assert result.ndcg_at_k == 0.0
    assert result.hit_rate_at_k == 0.0


def test_execute_computes_diversity_from_the_engines_actual_recommended_categories() -> None:
    """Two of three recommended items share a category -- diversity_at_k must
    reflect that repeat, proving it's computed from real item categories
    rather than always trivially 1.0 (as it is when each case has only one
    recommendation, the case covered above).
    """
    case = EvaluationCase(
        book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()})
    )
    dataset = EvaluationDataset(cases=(case,))

    class _RepeatedCategoryEngine(RecommendationEngine):
        def recommend(self, query: RecommendationQuery) -> RecommendationResult:
            categories = ["Fiction", "Fiction", "History"]
            items = [
                RecommendationItem(
                    book=Book(
                        id=BookId.generate(),
                        isbn=ISBN("978-3-16-148410-0"),
                        title=Title("Title"),
                        author=Author("Author"),
                        category=Category(category),
                    ),
                    score=1.0,
                    source="fake",
                )
                for category in categories[: query.limit]
            ]
            return RecommendationResult(recommendation=Recommendation(items=items))

    result = EvaluateRecommendationEngineUseCase().execute(
        _RepeatedCategoryEngine(), "fake", dataset, k=3
    )

    assert result.diversity_at_k == pytest.approx(2 / 3)
