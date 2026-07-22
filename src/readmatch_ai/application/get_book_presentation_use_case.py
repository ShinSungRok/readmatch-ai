from __future__ import annotations

import uuid

from readmatch_ai.application.book_presentation import BookPresentation, to_book_presentation
from readmatch_ai.domain.book import Book, BookId
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

    def execute_many(self, books: list[Book]) -> dict[str, BookPresentation]:
        """Batch-build presentations for Books a caller already has in hand.

        Used by callers building a list of presentations from an existing
        recommendation result (e.g. GetHomeFeedUseCase, GetBookDetailUseCase's
        similar books) -- avoids one BookMetadataRepository round-trip per
        book (a real N+1 otherwise) and never re-fetches from
        BookRepository, since the caller already has each Book. Keyed by
        the same string book id `execute()` itself takes/returns.
        """
        unique_books = {book.id: book for book in books}
        metadata_by_id = self._book_metadata_repository.get_by_book_ids(list(unique_books))
        return {
            str(book_id.value): to_book_presentation(book, metadata_by_id.get(book_id))
            for book_id, book in unique_books.items()
        }
