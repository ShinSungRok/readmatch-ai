import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine


class _FakeRecommendationEngine(RecommendationEngine):
    """Returns a fixed result regardless of the query, capturing the last query received."""

    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return RecommendationResult(recommendation=Recommendation(items=self._items))


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def _item(book: Book, score: float, source: str) -> RecommendationItem:
    return RecommendationItem(book=book, score=score, source=source)


def test_recommend_merges_and_sums_scores_for_a_book_in_both_engines() -> None:
    shared = _book("978-3-16-148410-0", "Shared")
    popularity_only = _book("0-306-40615-2", "PopularityOnly")
    semantic_only = _book("9780132350884", "SemanticOnly")
    popularity_engine = _FakeRecommendationEngine(
        [_item(shared, 100.0, "popularity"), _item(popularity_only, 10.0, "popularity")]
    )
    semantic_engine = _FakeRecommendationEngine(
        [_item(shared, 0.9, "semantic"), _item(semantic_only, 0.1, "semantic")]
    )
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine, popularity_weight=0.5)
    source_book_id = BookId.generate()

    result = engine.recommend(RecommendationQuery(limit=10, book_id=source_book_id))

    items_by_title = {item.book.title.value: item for item in result.recommendation.items}
    assert set(items_by_title) == {"Shared", "PopularityOnly", "SemanticOnly"}
    # Shared is top of both normalized lists (1.0 each side) -> 0.5*1.0 + 0.5*1.0 = 1.0
    assert items_by_title["Shared"].score == pytest.approx(1.0)
    assert items_by_title["Shared"].score > items_by_title["PopularityOnly"].score
    assert items_by_title["Shared"].score > items_by_title["SemanticOnly"].score
    assert all(item.source == "hybrid" for item in result.recommendation.items)


def test_recommend_respects_limit() -> None:
    popularity_engine = _FakeRecommendationEngine(
        [_item(_book(isbn), 10.0, "popularity") for isbn in ["978-3-16-148410-0", "0-306-40615-2"]]
    )
    semantic_engine = _FakeRecommendationEngine([])
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine)

    result = engine.recommend(RecommendationQuery(limit=1, book_id=BookId.generate()))

    assert len(result.recommendation.items) == 1


def test_recommend_falls_back_fully_to_popularity_when_no_source_book() -> None:
    book = _book("978-3-16-148410-0")
    popularity_engine = _FakeRecommendationEngine([_item(book, 10.0, "popularity")])
    semantic_engine = _FakeRecommendationEngine([_item(book, 0.5, "semantic")])
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine, popularity_weight=0.2)

    result = engine.recommend(RecommendationQuery(limit=10))

    assert semantic_engine.received_query is None
    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].score == pytest.approx(1.0)


def test_recommend_falls_back_fully_to_popularity_when_semantic_engine_has_no_results() -> None:
    book = _book("978-3-16-148410-0")
    popularity_engine = _FakeRecommendationEngine([_item(book, 10.0, "popularity")])
    semantic_engine = _FakeRecommendationEngine([])
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine, popularity_weight=0.2)

    result = engine.recommend(RecommendationQuery(limit=10, book_id=BookId.generate()))

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].score == pytest.approx(1.0)


def test_recommend_returns_empty_when_both_engines_have_no_results() -> None:
    popularity_engine = _FakeRecommendationEngine([])
    semantic_engine = _FakeRecommendationEngine([])
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine)

    result = engine.recommend(RecommendationQuery(limit=10, book_id=BookId.generate()))

    assert result.recommendation.items == []


def test_recommend_orders_by_configured_weight() -> None:
    popularity_favorite = _book("978-3-16-148410-0", "PopularityFavorite")
    semantic_favorite = _book("0-306-40615-2", "SemanticFavorite")
    popularity_engine = _FakeRecommendationEngine(
        [
            _item(popularity_favorite, 100.0, "popularity"),
            _item(semantic_favorite, 1.0, "popularity"),
        ]
    )
    semantic_engine = _FakeRecommendationEngine(
        [_item(semantic_favorite, 0.9, "semantic"), _item(popularity_favorite, 0.1, "semantic")]
    )
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine, popularity_weight=0.9)

    result = engine.recommend(RecommendationQuery(limit=10, book_id=BookId.generate()))

    assert result.recommendation.items[0].book.title.value == "PopularityFavorite"


@pytest.mark.parametrize("invalid_weight", [-0.1, 1.1])
def test_init_rejects_popularity_weight_outside_unit_interval(invalid_weight: float) -> None:
    with pytest.raises(ValueError, match="popularity_weight"):
        HybridRecommendationEngine(
            _FakeRecommendationEngine([]),
            _FakeRecommendationEngine([]),
            popularity_weight=invalid_weight,
        )
