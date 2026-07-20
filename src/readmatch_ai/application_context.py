from __future__ import annotations

from dataclasses import dataclass

import psycopg

from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.config import POSTGRESQL_BACKEND, BookRepositoryConfig
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.popularity_recommendation_engine import (
    PopularityRecommendationEngine,
)
from readmatch_ai.infrastructure.postgresql_book_popularity_repository import (
    PostgreSQLBookPopularityRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired repositories and use cases."""

    book_repository: BookRepository
    book_popularity_repository: BookPopularityRepository
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase
    get_recommendations_use_case: GetRecommendationsUseCase

    @classmethod
    def create(
        cls,
        book_repository: BookRepository | None = None,
        book_popularity_repository: BookPopularityRepository | None = None,
        recommendation_engine: RecommendationEngine | None = None,
    ) -> ApplicationContext:
        """Wire the Book/Recommendation use cases to their repositories and engine.

        book_repository/book_popularity_repository each default independently
        via BookRepositoryConfig.from_env(): the InMemory adapters, or the
        PostgreSQL adapters when BOOK_REPOSITORY_BACKEND=postgresql.
        recommendation_engine defaults to PopularityRecommendationEngine built
        from those same (already-resolved) repositories.
        """
        repository = book_repository if book_repository is not None else _build_book_repository()
        popularity_repository = (
            book_popularity_repository
            if book_popularity_repository is not None
            else _build_book_popularity_repository()
        )
        engine = (
            recommendation_engine
            if recommendation_engine is not None
            else PopularityRecommendationEngine(popularity_repository, repository)
        )
        return cls(
            book_repository=repository,
            book_popularity_repository=popularity_repository,
            register_book_use_case=RegisterBookUseCase(repository),
            get_book_by_id_use_case=GetBookByIdUseCase(repository),
            get_book_by_isbn_use_case=GetBookByISBNUseCase(repository),
            get_recommendations_use_case=GetRecommendationsUseCase(engine),
        )


def _build_book_repository() -> BookRepository:
    config = BookRepositoryConfig.from_env()
    if config.backend == POSTGRESQL_BACKEND:
        assert config.database_url is not None  # enforced by BookRepositoryConfig.from_env
        connection = psycopg.connect(config.database_url)
        return PostgreSQLBookRepository(connection)
    return InMemoryBookRepository()


def _build_book_popularity_repository() -> BookPopularityRepository:
    config = BookRepositoryConfig.from_env()
    if config.backend == POSTGRESQL_BACKEND:
        assert config.database_url is not None  # enforced by BookRepositoryConfig.from_env
        connection = psycopg.connect(config.database_url)
        return PostgreSQLBookPopularityRepository(connection)
    return InMemoryBookPopularityRepository()
