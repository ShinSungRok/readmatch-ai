from __future__ import annotations

import uuid

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.book_repository import BookRepository


class GetBookByIdUseCase:
    """Retrieves a Book by its id, delegating to BookRepository."""

    def __init__(self, book_repository: BookRepository) -> None:
        self._book_repository = book_repository

    def execute(self, book_id: str) -> Book | None:
        return self._book_repository.get_by_id(BookId(uuid.UUID(book_id)))
