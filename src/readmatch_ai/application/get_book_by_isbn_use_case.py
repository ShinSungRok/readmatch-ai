from __future__ import annotations

from readmatch_ai.domain.book import ISBN, Book
from readmatch_ai.domain.book_repository import BookRepository


class GetBookByISBNUseCase:
    """Retrieves a Book by its ISBN, delegating to BookRepository."""

    def __init__(self, book_repository: BookRepository) -> None:
        self._book_repository = book_repository

    def execute(self, isbn: str) -> Book | None:
        return self._book_repository.get_by_isbn(ISBN(isbn))
