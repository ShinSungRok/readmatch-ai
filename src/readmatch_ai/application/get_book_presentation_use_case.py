from __future__ import annotations

import uuid

from readmatch_ai.application.book_presentation import BookPresentation, to_book_presentation
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadataRepository
from readmatch_ai.domain.book_repository import BookRepository


class GetBookPresentationUseCase:
    """Retrieves UI-ready presentation data for a book, or None if it doesn't exist.

    Composes the existing BookRepository with BookMetadataRepository --
    no recommendation ranking or scoring logic involved.
    """

    def __init__(
        self, book_repository: BookRepository, book_metadata_repository: BookMetadataRepository
    ) -> None:
        self._book_repository = book_repository
        self._book_metadata_repository = book_metadata_repository

    def execute(self, book_id: str) -> BookPresentation | None:
        book = self._book_repository.get_by_id(BookId(uuid.UUID(book_id)))
        if book is None:
            return None
        metadata = self._book_metadata_repository.get_by_book_id(book.id)
        return to_book_presentation(book, metadata)
