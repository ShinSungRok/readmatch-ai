import uuid

from readmatch_ai.application.book_presentation import deterministic_cover_fallback
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def test_execute_returns_presentation_with_recorded_metadata() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    book = RegisterBookUseCase(book_repository).execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    metadata_repository.record(
        BookMetadata(book.id, publisher="Prentice Hall", description="A classic.")
    )
    use_case = GetBookPresentationUseCase(book_repository, metadata_repository)

    presentation = use_case.execute(str(book.id.value))

    assert presentation is not None
    assert presentation.title == "Clean Code"
    assert presentation.publisher == "Prentice Hall"
    assert presentation.description == "A classic."


def test_execute_returns_presentation_with_fallback_cover_when_metadata_missing() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    book = RegisterBookUseCase(book_repository).execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    use_case = GetBookPresentationUseCase(book_repository, metadata_repository)

    presentation = use_case.execute(str(book.id.value))

    assert presentation is not None
    assert presentation.publisher is None
    assert presentation.cover_url == deterministic_cover_fallback(str(book.id.value))


def test_execute_returns_none_when_book_does_not_exist() -> None:
    use_case = GetBookPresentationUseCase(
        InMemoryBookRepository(), InMemoryBookMetadataRepository()
    )

    assert use_case.execute(str(uuid.uuid4())) is None


def test_execute_many_enriches_each_book_with_its_own_recorded_metadata() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    with_metadata = register.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    without_metadata = register.execute(
        RegisterBookInput("0-306-40615-2", "Dune", "Frank Herbert", "Fiction")
    )
    metadata_repository.record(BookMetadata(with_metadata.id, publisher="Prentice Hall"))
    use_case = GetBookPresentationUseCase(book_repository, metadata_repository)

    presentations = use_case.execute_many([with_metadata, without_metadata])

    assert presentations[str(with_metadata.id.value)].publisher == "Prentice Hall"
    assert presentations[str(without_metadata.id.value)].publisher is None
    assert presentations[str(without_metadata.id.value)].cover_url == deterministic_cover_fallback(
        str(without_metadata.id.value)
    )


def test_execute_many_returns_empty_dict_for_empty_input() -> None:
    use_case = GetBookPresentationUseCase(
        InMemoryBookRepository(), InMemoryBookMetadataRepository()
    )

    assert use_case.execute_many([]) == {}


def test_execute_many_makes_exactly_one_batch_metadata_call_regardless_of_book_count() -> None:
    """Regression: GetHomeFeedUseCase/GetBookDetailUseCase build presentations
    for potentially dozens of items -- execute_many must batch that into one
    BookMetadataRepository round-trip, not one per book (a real N+1).
    """
    book_repository = InMemoryBookRepository()
    register = RegisterBookUseCase(book_repository)
    books = [
        register.execute(RegisterBookInput(isbn, f"Book {i}", "Author", "Fiction"))
        for i, isbn in enumerate(
            ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"], start=1
        )
    ]

    class _CountingMetadataRepository(InMemoryBookMetadataRepository):
        def __init__(self) -> None:
            super().__init__()
            self.batch_call_count = 0

        def get_by_book_ids(self, book_ids: list[BookId]) -> dict[BookId, BookMetadata]:
            self.batch_call_count += 1
            return super().get_by_book_ids(book_ids)

    metadata_repository = _CountingMetadataRepository()
    use_case = GetBookPresentationUseCase(book_repository, metadata_repository)

    presentations = use_case.execute_many(books)

    assert metadata_repository.batch_call_count == 1
    assert len(presentations) == len(books)
