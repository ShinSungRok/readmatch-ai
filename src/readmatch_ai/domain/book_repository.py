from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.book import ISBN, Book, BookId


class BookRepository(ABC):
    """Port for Book persistence; implemented by an infrastructure adapter."""

    @abstractmethod
    def add(self, book: Book) -> None: ...

    @abstractmethod
    def get_by_id(self, book_id: BookId) -> Book | None: ...

    @abstractmethod
    def get_by_isbn(self, isbn: ISBN) -> Book | None: ...
