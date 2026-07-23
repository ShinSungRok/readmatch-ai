from readmatch_ai.application.generate_reranked_recommendation_use_case import (
    GenerateRerankedRecommendationUseCase,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.home_feed import HomeFeedItem
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class FakeRecommendationEngine(RecommendationEngine):
    """Mocked RecommendationEngine capturing the query it was called with."""

    def __init__(self, result: RecommendationResult) -> None:
        self._result = result
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return self._result


def _book(isbn: str = "978-3-16-148410-0") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def _book_presentation_use_case(books: list[Book]) -> GetBookPresentationUseCase:
    """A real GetBookPresentationUseCase over an in-memory repository seeded
    with `books` -- the same reuse-a-real-lightweight-use-case convention
    established elsewhere in this test suite, not a hand-written fake.
    """
    book_repository = InMemoryBookRepository()
    for book in books:
        book_repository.add(book)
    return GetBookPresentationUseCase(book_repository, InMemoryBookMetadataRepository())


def test_execute_passes_book_id_and_limit_to_engine_as_recommendation_query() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([]))
    book_id = BookId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, book_id=book_id)


def test_execute_passes_none_book_id_when_omitted() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([]))

    use_case.execute(limit=5)

    assert engine.received_query == RecommendationQuery(limit=5, book_id=None)


def test_execute_passes_user_id_to_engine_as_recommendation_query() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([]))
    user_id = UserId.generate()

    use_case.execute(limit=5, user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, user_id=user_id)


def test_execute_passes_both_book_id_and_user_id_together() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([]))
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(
        limit=5, book_id=book_id, user_id=user_id
    )


def test_execute_returns_presentation_ready_items_matching_the_engine_result() -> None:
    book = _book()
    item = RecommendationItem(book=book, score=0.8, source="hybrid")
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    presentation_use_case = _book_presentation_use_case([book])
    use_case = GenerateRerankedRecommendationUseCase(engine, presentation_use_case)
    expected_presentation = presentation_use_case.execute(str(book.id.value))
    assert expected_presentation is not None

    result = use_case.execute(limit=10)

    assert result == [HomeFeedItem(book=expected_presentation, score=0.8, source="hybrid")]


def test_execute_includes_presentation_fields_the_bare_domain_book_lacks() -> None:
    """Regression guard: the personalized endpoint used to serialize the bare
    Domain Book (no cover_url/publisher/description/published_date), which
    the frontend's BookCard cannot render a cover from.
    """
    book = _book()
    item = RecommendationItem(book=book, score=0.8, source="hybrid")
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([book]))

    result = use_case.execute(limit=10)

    assert result[0].book.cover_url is not None and result[0].book.cover_url != ""


def test_execute_returns_empty_list_when_engine_has_no_recommendations() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    use_case = GenerateRerankedRecommendationUseCase(engine, _book_presentation_use_case([]))

    result = use_case.execute(limit=10)

    assert result == []


def test_execute_looks_up_presentation_metadata_in_one_batch_call() -> None:
    """Regression: N+1 guard -- one BookMetadataRepository round-trip for
    the whole result set, never one per item.
    """

    class _CountingMetadataRepository(InMemoryBookMetadataRepository):
        def __init__(self) -> None:
            super().__init__()
            self.batch_call_count = 0

        def get_by_book_ids(self, book_ids: list[BookId]) -> dict[BookId, BookMetadata]:
            self.batch_call_count += 1
            return super().get_by_book_ids(book_ids)

    books = [
        _book(isbn)
        for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]
    ]
    book_repository = InMemoryBookRepository()
    for book in books:
        book_repository.add(book)
    metadata_repository = _CountingMetadataRepository()
    presentation_use_case = GetBookPresentationUseCase(book_repository, metadata_repository)
    items = [RecommendationItem(book=book, score=0.5, source="hybrid") for book in books]
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=items)))
    use_case = GenerateRerankedRecommendationUseCase(engine, presentation_use_case)

    result = use_case.execute(limit=10)

    assert len(result) == 3
    assert metadata_repository.batch_call_count == 1
