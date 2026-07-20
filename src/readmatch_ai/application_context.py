from __future__ import annotations

from dataclasses import dataclass

import psycopg

from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.config import POSTGRESQL_BACKEND, BookRepositoryConfig
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired BookRepository and Book use cases."""

    book_repository: BookRepository
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase

    @classmethod
    def create(cls, book_repository: BookRepository | None = None) -> ApplicationContext:
        """Wire the Book use cases to a BookRepository.

        Defaults to BookRepositoryConfig.from_env(): the InMemory adapter, or
        the PostgreSQL adapter when BOOK_REPOSITORY_BACKEND=postgresql.
        """
        repository = book_repository if book_repository is not None else _build_book_repository()
        return cls(
            book_repository=repository,
            register_book_use_case=RegisterBookUseCase(repository),
            get_book_by_id_use_case=GetBookByIdUseCase(repository),
            get_book_by_isbn_use_case=GetBookByISBNUseCase(repository),
        )


def _build_book_repository() -> BookRepository:
    config = BookRepositoryConfig.from_env()
    if config.backend == POSTGRESQL_BACKEND:
        assert config.database_url is not None  # enforced by BookRepositoryConfig.from_env
        connection = psycopg.connect(config.database_url)
        return PostgreSQLBookRepository(connection)
    return InMemoryBookRepository()
