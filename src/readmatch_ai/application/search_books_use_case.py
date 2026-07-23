from __future__ import annotations

from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.domain.book_repository import BookRepository


class SearchBooksUseCase:
    """Searches books by title/author/category, returning presentation-ready results.

    Delegates the actual case-insensitive partial-match query to
    BookRepository.search (Domain port); this only applies input policy
    (trim, reject a blank query) and enriches each match into a
    BookPresentation via the existing GetBookPresentationUseCase --
    execute_many looks up every match's metadata in one
    BookMetadataRepository round-trip, never one per book (no N+1).
    """

    def __init__(
        self,
        book_repository: BookRepository,
        book_presentation_use_case: GetBookPresentationUseCase,
    ) -> None:
        self._book_repository = book_repository
        self._book_presentation_use_case = book_presentation_use_case

    def execute(self, query: str, limit: int = 20) -> list[BookPresentation]:
        """Returns an empty list for a blank (or whitespace-only) query -- a
        valid, safe response, never an error and never "every book".
        """
        normalized_query = query.strip()
        if not normalized_query:
            return []

        books = self._book_repository.search(normalized_query, limit)
        presentations = self._book_presentation_use_case.execute_many(books)
        return [presentations[str(book.id.value)] for book in books]
