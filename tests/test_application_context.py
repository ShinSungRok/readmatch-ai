import uuid

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class _FakeRecommendationEngine(RecommendationEngine):
    def __init__(self, result: RecommendationResult) -> None:
        self._result = result

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        return self._result


def _valid_input() -> RegisterBookInput:
    return RegisterBookInput(
        isbn="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        category="Software Engineering",
    )


def test_create_defaults_to_in_memory_repository() -> None:
    context = ApplicationContext.create()

    assert isinstance(context.book_repository, InMemoryBookRepository)


def test_create_accepts_an_explicit_repository() -> None:
    repository = InMemoryBookRepository()

    context = ApplicationContext.create(book_repository=repository)

    assert context.book_repository is repository


def test_use_cases_share_the_same_repository_instance() -> None:
    context = ApplicationContext.create()

    book = context.register_book_use_case.execute(_valid_input())

    assert context.get_book_by_id_use_case.execute(str(book.id.value)) == book
    assert context.get_book_by_isbn_use_case.execute("978-3-16-148410-0") == book


def test_missing_book_lookups_return_none() -> None:
    context = ApplicationContext.create()

    assert context.get_book_by_id_use_case.execute(str(uuid.uuid4())) is None
    assert context.get_book_by_isbn_use_case.execute("0-306-40615-2") is None


def test_create_calls_are_independent() -> None:
    first_context = ApplicationContext.create()
    second_context = ApplicationContext.create()

    first_context.register_book_use_case.execute(_valid_input())

    assert second_context.get_book_by_isbn_use_case.execute("978-3-16-148410-0") is None


def test_recommendations_reflect_persisted_popularity() -> None:
    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())
    context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    result = context.get_recommendations_use_case.execute(limit=10)

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book == book
    assert result.recommendation.items[0].source == "popularity"


def test_create_accepts_an_explicit_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(recommendation_engine=engine)

    assert context.get_recommendations_use_case.execute(limit=1) is sentinel_result
