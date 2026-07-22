import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata, BookMetadataRepository


def test_book_metadata_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookMetadataRepository()  # type: ignore[abstract]


def test_book_metadata_fields_default_to_none() -> None:
    metadata = BookMetadata(book_id=BookId.generate())

    assert metadata.publisher is None
    assert metadata.description is None
    assert metadata.cover_url is None
    assert metadata.published_date is None
