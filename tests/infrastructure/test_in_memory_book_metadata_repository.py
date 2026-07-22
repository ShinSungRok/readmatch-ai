from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)


def test_get_by_book_id_returns_the_recorded_metadata() -> None:
    repository = InMemoryBookMetadataRepository()
    book_id = BookId.generate()
    metadata = BookMetadata(
        book_id, publisher="Publisher", description="Description", published_date="2020-01-01"
    )

    repository.record(metadata)

    assert repository.get_by_book_id(book_id) == metadata


def test_get_by_book_id_returns_none_when_never_recorded() -> None:
    repository = InMemoryBookMetadataRepository()

    assert repository.get_by_book_id(BookId.generate()) is None


def test_record_upserts_existing_book_id() -> None:
    repository = InMemoryBookMetadataRepository()
    book_id = BookId.generate()
    repository.record(BookMetadata(book_id, publisher="Old"))

    repository.record(BookMetadata(book_id, publisher="New"))

    assert repository.get_by_book_id(book_id) == BookMetadata(book_id, publisher="New")
