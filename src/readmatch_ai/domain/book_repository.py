from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.book import ISBN, Book, BookId


class BookNotFoundError(Exception):
    """Raised when a repository operation targets a Book that does not exist."""


class DuplicateISBNError(Exception):
    """Raised when adding or updating a Book would violate ISBN uniqueness."""


class BookRepository(ABC):
    """Port for Book persistence; implemented by an infrastructure adapter."""

    @abstractmethod
    def add(self, book: Book) -> None: ...

    @abstractmethod
    def get_by_id(self, book_id: BookId) -> Book | None: ...

    @abstractmethod
    def get_by_isbn(self, isbn: ISBN) -> Book | None: ...

    @abstractmethod
    def update(self, book: Book) -> None:
        """Update an existing Book; raises BookNotFoundError if it does not exist."""

    @abstractmethod
    def remove(self, book_id: BookId) -> None:
        """Remove an existing Book; raises BookNotFoundError if it does not exist."""
