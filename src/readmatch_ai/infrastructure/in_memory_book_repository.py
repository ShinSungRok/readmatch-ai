from __future__ import annotations

from readmatch_ai.domain.book import ISBN, Book, BookId
from readmatch_ai.domain.book_repository import (
    BookNotFoundError,
    BookRepository,
    DuplicateISBNError,
)


class InMemoryBookRepository(BookRepository):
    """In-process BookRepository adapter backed by a dict; no external storage."""

    def __init__(self) -> None:
        self._books: dict[BookId, Book] = {}

    def add(self, book: Book) -> None:
        if self._has_isbn_conflict(book):
            raise DuplicateISBNError(f"ISBN already exists: {book.isbn.value}")
        self._books[book.id] = book

    def get_by_id(self, book_id: BookId) -> Book | None:
        return self._books.get(book_id)

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        return next((b for b in self._books.values() if b.isbn == isbn), None)

    def list_all(self) -> list[Book]:
        return list(self._books.values())

    def update(self, book: Book) -> None:
        if book.id not in self._books:
            raise BookNotFoundError(f"Book not found: {book.id}")
        if self._has_isbn_conflict(book):
            raise DuplicateISBNError(f"ISBN already exists: {book.isbn.value}")
        self._books[book.id] = book

    def _has_isbn_conflict(self, book: Book) -> bool:
        return any(
            existing.isbn == book.isbn and existing.id != book.id
            for existing in self._books.values()
        )

    def remove(self, book_id: BookId) -> None:
        if book_id not in self._books:
            raise BookNotFoundError(f"Book not found: {book_id}")
        del self._books[book_id]
