from __future__ import annotations

from dataclasses import dataclass

import psycopg

from readmatch_ai.application.generate_book_embedding_use_case import (
    GenerateBookEmbeddingUseCase,
)
from readmatch_ai.application.generate_hybrid_recommendation_use_case import (
    GenerateHybridRecommendationUseCase,
)
from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.config import POSTGRESQL_BACKEND, BookRepositoryConfig
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.popularity_recommendation_engine import (
    PopularityRecommendationEngine,
)
from readmatch_ai.infrastructure.postgresql_book_embedding_repository import (
    PostgreSQLBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.postgresql_book_popularity_repository import (
    PostgreSQLBookPopularityRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired repositories and use cases."""

    book_repository: BookRepository
    book_popularity_repository: BookPopularityRepository
    book_embedding_repository: BookEmbeddingRepository
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase
    get_recommendations_use_case: GetRecommendationsUseCase
    generate_book_embedding_use_case: GenerateBookEmbeddingUseCase
    generate_semantic_recommendation_use_case: GenerateSemanticRecommendationUseCase
    generate_hybrid_recommendation_use_case: GenerateHybridRecommendationUseCase

    @classmethod
    def create(
        cls,
        book_repository: BookRepository | None = None,
        book_popularity_repository: BookPopularityRepository | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        book_embedding_repository: BookEmbeddingRepository | None = None,
        book_embedding_generator: BookEmbeddingGenerator | None = None,
        semantic_recommendation_engine: RecommendationEngine | None = None,
        hybrid_recommendation_engine: RecommendationEngine | None = None,
    ) -> ApplicationContext:
        """Wire the Book/Recommendation/Embedding use cases to their dependencies.

        book_repository/book_popularity_repository each default independently
        via BookRepositoryConfig.from_env(): the InMemory adapters, or the
        PostgreSQL adapters when BOOK_REPOSITORY_BACKEND=postgresql.
        recommendation_engine defaults to PopularityRecommendationEngine built
        from those same (already-resolved) repositories.
        book_embedding_repository defaults via the same
        BookRepositoryConfig.from_env() as the other two repositories:
        InMemoryBookEmbeddingRepository (preserved as the default whenever
        the backend is unset/in_memory) or PostgreSQLBookEmbeddingRepository
        when BOOK_REPOSITORY_BACKEND=postgresql. book_embedding_generator
        defaults to DeterministicFakeBookEmbeddingGenerator (no real model
        yet). semantic_recommendation_engine defaults to
        SemanticRecommendationEngine built from those same (already-resolved)
        book_embedding_repository/book_repository. hybrid_recommendation_engine
        defaults to HybridRecommendationEngine built from the same
        (already-resolved) popularity/semantic engines used above — an
        explicit override of either of those also flows into the default
        Hybrid engine, keeping composition consistent.
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
        embedding_repository = (
            book_embedding_repository
            if book_embedding_repository is not None
            else _build_book_embedding_repository()
        )
        embedding_generator = (
            book_embedding_generator
            if book_embedding_generator is not None
            else DeterministicFakeBookEmbeddingGenerator()
        )
        semantic_engine = (
            semantic_recommendation_engine
            if semantic_recommendation_engine is not None
            else SemanticRecommendationEngine(embedding_repository, repository)
        )
        hybrid_engine = (
            hybrid_recommendation_engine
            if hybrid_recommendation_engine is not None
            else HybridRecommendationEngine(engine, semantic_engine)
        )
        return cls(
            book_repository=repository,
            book_popularity_repository=popularity_repository,
            book_embedding_repository=embedding_repository,
            register_book_use_case=RegisterBookUseCase(repository),
            get_book_by_id_use_case=GetBookByIdUseCase(repository),
            get_book_by_isbn_use_case=GetBookByISBNUseCase(repository),
            get_recommendations_use_case=GetRecommendationsUseCase(engine),
            generate_book_embedding_use_case=GenerateBookEmbeddingUseCase(
                repository, embedding_generator, embedding_repository
            ),
            generate_semantic_recommendation_use_case=GenerateSemanticRecommendationUseCase(
                semantic_engine
            ),
            generate_hybrid_recommendation_use_case=GenerateHybridRecommendationUseCase(
                hybrid_engine
            ),
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


def _build_book_embedding_repository() -> BookEmbeddingRepository:
    config = BookRepositoryConfig.from_env()
    if config.backend == POSTGRESQL_BACKEND:
        assert config.database_url is not None  # enforced by BookRepositoryConfig.from_env
        connection = psycopg.connect(config.database_url)
        return PostgreSQLBookEmbeddingRepository(connection)
    return InMemoryBookEmbeddingRepository()
