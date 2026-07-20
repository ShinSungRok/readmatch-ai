from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired BookRepository and Book use cases."""

    book_repository: BookRepository
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase

    @classmethod
    def create(cls, book_repository: BookRepository | None = None) -> ApplicationContext:
        """Wire the Book use cases to a BookRepository (defaults to the InMemory adapter)."""
        repository = book_repository if book_repository is not None else InMemoryBookRepository()
        return cls(
            book_repository=repository,
            register_book_use_case=RegisterBookUseCase(repository),
            get_book_by_id_use_case=GetBookByIdUseCase(repository),
            get_book_by_isbn_use_case=GetBookByISBNUseCase(repository),
        )
