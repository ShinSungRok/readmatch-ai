from readmatch_ai.application.generate_hybrid_recommendation_use_case import (
    GenerateHybridRecommendationUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


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


def test_execute_passes_book_id_and_limit_to_engine_as_recommendation_query() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)
    book_id = BookId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, book_id=book_id)


def test_execute_passes_none_book_id_when_omitted() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)

    use_case.execute(limit=5)

    assert engine.received_query == RecommendationQuery(limit=5, book_id=None)


def test_execute_passes_user_id_to_engine_as_recommendation_query() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)
    user_id = UserId.generate()

    use_case.execute(limit=5, user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, user_id=user_id)


def test_execute_passes_none_user_id_when_omitted() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)

    use_case.execute(limit=5)

    assert engine.received_query == RecommendationQuery(limit=5, user_id=None)


def test_execute_passes_both_book_id_and_user_id_together() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(
        limit=5, book_id=book_id, user_id=user_id
    )


def test_execute_returns_engine_result() -> None:
    item = RecommendationItem(book=_book(), score=0.8, source="hybrid")
    expected_result = RecommendationResult(Recommendation(items=[item]))
    engine = FakeRecommendationEngine(expected_result)
    use_case = GenerateHybridRecommendationUseCase(engine)

    result = use_case.execute(limit=10)

    assert result == expected_result


def test_execute_returns_empty_result_when_engine_has_no_recommendations() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateHybridRecommendationUseCase(engine)

    result = use_case.execute(limit=10)

    assert result.recommendation.items == []
