from __future__ import annotations

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata, BookMetadataRepository


class InMemoryBookMetadataRepository(BookMetadataRepository):
    """In-process BookMetadataRepository adapter backed by a dict."""

    def __init__(self) -> None:
        self._metadata: dict[BookId, BookMetadata] = {}

    def record(self, metadata: BookMetadata) -> None:
        self._metadata[metadata.book_id] = metadata

    def get_by_book_id(self, book_id: BookId) -> BookMetadata | None:
        return self._metadata.get(book_id)
