import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.reranker import RecommendationReranker, RerankingContext
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.reranked_recommendation_engine import RerankedRecommendationEngine


class _FakeRecommendationEngine(RecommendationEngine):
    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return RecommendationResult(recommendation=Recommendation(items=self._items))


class _RecordingReranker(RecommendationReranker):
    def __init__(self, result: list[RecommendationItem]) -> None:
        self._result = result
        self.received_items: list[RecommendationItem] | None = None
        self.received_limit: int | None = None
        self.received_context: RerankingContext | None = None

    def rerank(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        self.received_items = items
        self.received_limit = limit
        self.received_context = context
        return self._result


def _book(isbn: str) -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Title"),
        author=Author("Author"),
        category=Category("Category"),
    )


def _item(book: Book, score: float) -> RecommendationItem:
    return RecommendationItem(book=book, score=score, source="fake")


def test_rejects_a_candidate_multiplier_below_one() -> None:
    with pytest.raises(ValueError, match="candidate_multiplier"):
        RerankedRecommendationEngine(
            _FakeRecommendationEngine([]), _RecordingReranker([]), candidate_multiplier=0
        )


def test_recommend_over_fetches_from_the_inner_engine() -> None:
    inner_engine = _FakeRecommendationEngine([])
    reranker = _RecordingReranker([])
    engine = RerankedRecommendationEngine(inner_engine, reranker, candidate_multiplier=3)

    engine.recommend(RecommendationQuery(limit=5))

    assert inner_engine.received_query is not None
    assert inner_engine.received_query.limit == 15


def test_recommend_forwards_book_id_and_user_id_to_the_inner_engine() -> None:
    inner_engine = _FakeRecommendationEngine([])
    engine = RerankedRecommendationEngine(inner_engine, _RecordingReranker([]))
    book_id = BookId.generate()
    user_id = UserId.generate()

    engine.recommend(RecommendationQuery(limit=5, book_id=book_id, user_id=user_id))

    assert inner_engine.received_query is not None
    assert inner_engine.received_query.book_id == book_id
    assert inner_engine.received_query.user_id == user_id


def test_recommend_passes_candidates_original_limit_and_context_to_the_reranker() -> None:
    candidates = [_item(_book("978-3-16-148410-0"), 1.0)]
    inner_engine = _FakeRecommendationEngine(candidates)
    reranker = _RecordingReranker([])
    engine = RerankedRecommendationEngine(inner_engine, reranker)
    user_id = UserId.generate()

    engine.recommend(RecommendationQuery(limit=5, user_id=user_id))

    assert reranker.received_items == candidates
    assert reranker.received_limit == 5
    assert reranker.received_context == RerankingContext(user_id=user_id)


def test_recommend_returns_the_rerankers_result() -> None:
    expected_items = [_item(_book("978-3-16-148410-0"), 0.9)]
    engine = RerankedRecommendationEngine(
        _FakeRecommendationEngine([]), _RecordingReranker(expected_items)
    )

    result = engine.recommend(RecommendationQuery(limit=5))

    assert result.recommendation.items == expected_items
