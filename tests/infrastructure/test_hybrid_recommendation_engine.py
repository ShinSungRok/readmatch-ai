from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.ranking_strategy import RankingCandidateList, RankingStrategy
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.hybrid_recommendation_engine import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    HybridRecommendationEngine,
)


class _FakeRecommendationEngine(RecommendationEngine):
    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return RecommendationResult(recommendation=Recommendation(items=self._items))


class _RecordingRankingStrategy(RankingStrategy):
    """Captures the candidate lists/limit it was called with; returns a fixed result.

    HybridRecommendationEngine delegates all fusion math to the injected
    RankingStrategy, so its own tests only need to verify correct candidate
    assembly and delegation -- fusion algorithms are tested independently
    in tests/domain/test_ranking_strategies.py.
    """

    def __init__(self, result: list[RecommendationItem]) -> None:
        self._result = result
        self.received_candidate_lists: list[RankingCandidateList] | None = None
        self.received_limit: int | None = None

    def fuse(
        self, candidate_lists: list[RankingCandidateList], limit: int
    ) -> list[RecommendationItem]:
        self.received_candidate_lists = candidate_lists
        self.received_limit = limit
        return self._result


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


def _engine(strategy: RankingStrategy) -> tuple[
    HybridRecommendationEngine,
    _FakeRecommendationEngine,
    _FakeRecommendationEngine,
    _FakeRecommendationEngine,
]:
    popularity_engine = _FakeRecommendationEngine([])
    semantic_engine = _FakeRecommendationEngine([])
    als_engine = _FakeRecommendationEngine([])
    engine = HybridRecommendationEngine(popularity_engine, semantic_engine, als_engine, strategy)
    return engine, popularity_engine, semantic_engine, als_engine


def test_recommend_always_queries_popularity() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, popularity_engine, _, _ = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=5))

    assert popularity_engine.received_query is not None
    assert strategy.received_candidate_lists is not None
    assert [cl.source for cl in strategy.received_candidate_lists] == [POPULARITY_SOURCE]


def test_recommend_queries_semantic_only_when_book_id_is_set() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, semantic_engine, _ = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=5, book_id=BookId.generate()))

    assert semantic_engine.received_query is not None
    assert strategy.received_candidate_lists is not None
    sources = [cl.source for cl in strategy.received_candidate_lists]
    assert SEMANTIC_SOURCE in sources


def test_recommend_does_not_query_semantic_without_book_id() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, semantic_engine, _ = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=5))

    assert semantic_engine.received_query is None
    assert strategy.received_candidate_lists is not None
    sources = [cl.source for cl in strategy.received_candidate_lists]
    assert SEMANTIC_SOURCE not in sources


def test_recommend_queries_als_only_when_user_id_is_set() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, _, als_engine = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=5, user_id=UserId.generate()))

    assert als_engine.received_query is not None
    assert strategy.received_candidate_lists is not None
    sources = [cl.source for cl in strategy.received_candidate_lists]
    assert ALS_SOURCE in sources


def test_recommend_does_not_query_als_without_user_id() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, _, als_engine = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=5))

    assert als_engine.received_query is None
    assert strategy.received_candidate_lists is not None
    sources = [cl.source for cl in strategy.received_candidate_lists]
    assert ALS_SOURCE not in sources


def test_recommend_queries_all_three_when_book_id_and_user_id_are_both_set() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, _, _ = _engine(strategy)

    engine.recommend(
        RecommendationQuery(limit=5, book_id=BookId.generate(), user_id=UserId.generate())
    )

    assert strategy.received_candidate_lists is not None
    sources = {cl.source for cl in strategy.received_candidate_lists}
    assert sources == {POPULARITY_SOURCE, SEMANTIC_SOURCE, ALS_SOURCE}


def test_recommend_passes_limit_to_the_strategy() -> None:
    strategy = _RecordingRankingStrategy([])
    engine, _, _, _ = _engine(strategy)

    engine.recommend(RecommendationQuery(limit=7))

    assert strategy.received_limit == 7


def test_recommend_returns_the_strategys_fused_result() -> None:
    expected_items = [_item(_book("978-3-16-148410-0"), 0.9, "hybrid")]
    strategy = _RecordingRankingStrategy(expected_items)
    engine, _, _, _ = _engine(strategy)

    result = engine.recommend(RecommendationQuery(limit=5))

    assert result.recommendation.items == expected_items
