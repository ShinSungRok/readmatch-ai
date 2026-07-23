from readmatch_ai.application.book_presentation import deterministic_cover_fallback
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.application.search_books_use_case import SearchBooksUseCase
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def _build(
    metadata_repository: InMemoryBookMetadataRepository | None = None,
) -> tuple[SearchBooksUseCase, InMemoryBookRepository, RegisterBookUseCase]:
    book_repository = InMemoryBookRepository()
    presentation_use_case = GetBookPresentationUseCase(
        book_repository, metadata_repository or InMemoryBookMetadataRepository()
    )
    use_case = SearchBooksUseCase(book_repository, presentation_use_case)
    return use_case, book_repository, RegisterBookUseCase(book_repository)


def test_execute_returns_empty_list_for_blank_query() -> None:
    use_case, _, register = _build()
    register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    assert use_case.execute("") == []
    assert use_case.execute("   ") == []


def test_execute_trims_the_query_before_searching() -> None:
    use_case, _, register = _build()
    book = register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    results = use_case.execute("  clean  ")

    assert [p.id for p in results] == [str(book.id.value)]


def test_execute_returns_presentation_ready_matches_with_metadata() -> None:
    metadata_repository = InMemoryBookMetadataRepository()
    use_case, _, register = _build(metadata_repository)
    book = register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    metadata_repository.record(BookMetadata(book.id, publisher="Prentice Hall"))

    results = use_case.execute("clean code")

    assert len(results) == 1
    assert results[0].title == "Clean Code"
    assert results[0].publisher == "Prentice Hall"


def test_execute_returns_fallback_cover_when_metadata_missing() -> None:
    use_case, _, register = _build()
    book = register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    results = use_case.execute("clean")

    assert results[0].cover_url == deterministic_cover_fallback(str(book.id.value))


def test_execute_returns_empty_list_when_nothing_matches() -> None:
    use_case, _, register = _build()
    register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    assert use_case.execute("nonexistent") == []


def test_execute_respects_the_limit() -> None:
    use_case, _, register = _build()
    for i, isbn in enumerate(["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]):
        register.execute(RegisterBookInput(isbn, f"Software Book {i}", "Author", "Software"))

    assert len(use_case.execute("software", limit=2)) == 2


def test_execute_makes_exactly_one_batch_metadata_call_for_multiple_matches() -> None:
    """Regression: N+1 guard -- one BookMetadataRepository round-trip for
    the whole result set, never one per matched book.
    """

    class _CountingMetadataRepository(InMemoryBookMetadataRepository):
        def __init__(self) -> None:
            super().__init__()
            self.batch_call_count = 0

        def get_by_book_ids(self, book_ids: list[BookId]) -> dict[BookId, BookMetadata]:
            self.batch_call_count += 1
            return super().get_by_book_ids(book_ids)

    metadata_repository = _CountingMetadataRepository()
    use_case, _, register = _build(metadata_repository)
    for i, isbn in enumerate(["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]):
        register.execute(RegisterBookInput(isbn, f"Software Book {i}", "Author", "Software"))

    results = use_case.execute("software")

    assert len(results) == 3
    assert metadata_repository.batch_call_count == 1
