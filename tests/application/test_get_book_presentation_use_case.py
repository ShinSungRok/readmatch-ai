import uuid

from readmatch_ai.application.book_presentation import deterministic_cover_fallback
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
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
