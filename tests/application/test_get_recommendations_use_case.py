from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class FakeRecommendationEngine(RecommendationEngine):
    """Mocked RecommendationEngine capturing the query it was called with."""

    def __init__(self, result: RecommendationResult) -> None:
        self._result = result
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return self._result


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_execute_passes_limit_to_engine_as_recommendation_query() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GetRecommendationsUseCase(engine)

    use_case.execute(limit=7)

    assert engine.received_query == RecommendationQuery(limit=7)


def test_execute_returns_engine_result() -> None:
    item = RecommendationItem(book=_book(), score=100.0, source="popularity")
    expected_result = RecommendationResult(Recommendation(items=[item]))
    engine = FakeRecommendationEngine(expected_result)
    use_case = GetRecommendationsUseCase(engine)

    result = use_case.execute(limit=10)

    assert result == expected_result


def test_execute_returns_empty_result_when_engine_has_no_recommendations() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GetRecommendationsUseCase(engine)

    result = use_case.execute(limit=10)

    assert result.recommendation.items == []
