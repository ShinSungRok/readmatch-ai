import uuid

from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_detail_use_case import GetBookDetailUseCase
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.recommendation import (
    SEMANTIC_SOURCE,
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class _StubEngine(RecommendationEngine):
    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items
        self.last_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.last_query = query
        return RecommendationResult(recommendation=Recommendation(items=self._items))


def test_execute_returns_none_when_book_does_not_exist() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    use_case = GetBookDetailUseCase(
        GetBookPresentationUseCase(book_repository, metadata_repository),
        GenerateSemanticRecommendationUseCase(_StubEngine([])),
    )

    assert use_case.execute(str(uuid.uuid4())) is None


def test_execute_returns_the_book_and_its_similar_books() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    book = register.execute(RegisterBookInput("978-3-16-148410-0", "Book", "Author", "Fiction"))
    other = register.execute(RegisterBookInput("0-306-40615-2", "Other", "Author", "Fiction"))
    similar_item = RecommendationItem(book=other, score=0.9, source=SEMANTIC_SOURCE)
    semantic_engine = _StubEngine([similar_item])
    use_case = GetBookDetailUseCase(
        GetBookPresentationUseCase(book_repository, metadata_repository),
        GenerateSemanticRecommendationUseCase(semantic_engine),
    )

    detail = use_case.execute(str(book.id.value))

    assert detail is not None
    assert detail.book.id == str(book.id.value)
    assert detail.book.title == "Book"
    assert semantic_engine.last_query is not None
    assert semantic_engine.last_query.book_id == book.id
    assert len(detail.similar_books) == 1
    assert detail.similar_books[0].book.id == str(other.id.value)
    assert detail.similar_books[0].score == 0.9
    assert detail.similar_books[0].source == SEMANTIC_SOURCE


def test_execute_returns_no_similar_books_when_semantic_has_no_results() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    book = register.execute(RegisterBookInput("978-3-16-148410-0", "Book", "Author", "Fiction"))
    use_case = GetBookDetailUseCase(
        GetBookPresentationUseCase(book_repository, metadata_repository),
        GenerateSemanticRecommendationUseCase(_StubEngine([])),
    )

    detail = use_case.execute(str(book.id.value))

    assert detail is not None
    assert detail.similar_books == []
