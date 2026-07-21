from __future__ import annotations

from dataclasses import dataclass

import psycopg

from readmatch_ai.application.evaluate_recommendation_engine_use_case import (
    EvaluateRecommendationEngineUseCase,
)
from readmatch_ai.application.generate_als_recommendation_use_case import (
    GenerateAlsRecommendationUseCase,
)
from readmatch_ai.application.generate_book_embedding_use_case import (
    GenerateBookEmbeddingUseCase,
)
from readmatch_ai.application.generate_hybrid_recommendation_use_case import (
    GenerateHybridRecommendationUseCase,
)
from readmatch_ai.application.generate_reranked_recommendation_use_case import (
    GenerateRerankedRecommendationUseCase,
)
from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.config import (
    POSTGRESQL_BACKEND,
    RRF_STRATEGY,
    SENTENCE_TRANSFORMERS_BACKEND,
    AlsModelConfig,
    BookRepositoryConfig,
    EmbeddingGeneratorConfig,
    HybridRankingConfig,
)
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.ranking_strategies import (
    ReciprocalRankFusionStrategy,
    WeightedScoreFusionStrategy,
)
from readmatch_ai.domain.ranking_strategy import RankingStrategy
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.reranker import DefaultRecommendationReranker, RecommendationReranker
from readmatch_ai.domain.reranking_policies import (
    MMRDiversityPolicy,
    NoveltyBoostPolicy,
    PopularityPenaltyPolicy,
)
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository
from readmatch_ai.infrastructure.als_model import train_als_model
from readmatch_ai.infrastructure.als_model_store import AlsModelFileStore
from readmatch_ai.infrastructure.als_recommendation_engine import ALSRecommendationEngine
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)
from readmatch_ai.infrastructure.hybrid_recommendation_engine import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    HybridRecommendationEngine,
)
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)
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
from readmatch_ai.infrastructure.postgresql_user_book_interaction_repository import (
    PostgreSQLUserBookInteractionRepository,
)
from readmatch_ai.infrastructure.reranked_recommendation_engine import (
    RerankedRecommendationEngine,
)
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired repositories and use cases."""

    book_repository: BookRepository
    book_popularity_repository: BookPopularityRepository
    book_embedding_repository: BookEmbeddingRepository
    user_book_interaction_repository: UserBookInteractionRepository
    recommendation_engine: RecommendationEngine
    semantic_recommendation_engine: RecommendationEngine
    hybrid_recommendation_engine: RecommendationEngine
    als_recommendation_engine: RecommendationEngine
    reranked_recommendation_engine: RecommendationEngine
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase
    get_recommendations_use_case: GetRecommendationsUseCase
    generate_book_embedding_use_case: GenerateBookEmbeddingUseCase
    generate_semantic_recommendation_use_case: GenerateSemanticRecommendationUseCase
    generate_hybrid_recommendation_use_case: GenerateHybridRecommendationUseCase
    generate_als_recommendation_use_case: GenerateAlsRecommendationUseCase
    generate_reranked_recommendation_use_case: GenerateRerankedRecommendationUseCase
    evaluate_recommendation_engine_use_case: EvaluateRecommendationEngineUseCase

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
        user_book_interaction_repository: UserBookInteractionRepository | None = None,
        als_recommendation_engine: RecommendationEngine | None = None,
        reranked_recommendation_engine: RecommendationEngine | None = None,
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
        defaults via EmbeddingGeneratorConfig.from_env():
        DeterministicFakeBookEmbeddingGenerator (default, and the default
        stays deterministic even when unset — unlike the repository
        backends) or SentenceTransformerBookEmbeddingGenerator when
        EMBEDDING_GENERATOR_BACKEND=sentence_transformers.
        semantic_recommendation_engine defaults to
        SemanticRecommendationEngine built from those same (already-resolved)
        book_embedding_repository/book_repository.

        user_book_interaction_repository defaults via the same
        BookRepositoryConfig.from_env() as the other repositories.
        als_recommendation_engine defaults to an ALSRecommendationEngine
        wrapping a model resolved via AlsModelConfig.from_env(): loaded from
        ALS_MODEL_PATH if set and present, otherwise trained fresh
        in-process from user_book_interaction_repository's current
        contents (and saved to ALS_MODEL_PATH afterwards if that was set)
        — training is a batch/Infrastructure concern (see
        infrastructure.als_model), so this engine reflects a snapshot, not
        interactions recorded after it was built.

        hybrid_recommendation_engine defaults to HybridRecommendationEngine
        built from the same (already-resolved) popularity/semantic/ALS
        engines used above — an explicit override of any of those also
        flows into the default Hybrid engine, keeping composition
        consistent — paired with a RankingStrategy resolved via
        HybridRankingConfig.from_env(): WeightedScoreFusionStrategy
        (default) or ReciprocalRankFusionStrategy when
        HYBRID_RANKING_STRATEGY=rrf. Swapping strategies is a Composition
        Root concern only; neither HybridRecommendationEngine nor the
        Application layer changes either way.

        reranked_recommendation_engine defaults to a
        RerankedRecommendationEngine wrapping the same (already-resolved)
        hybrid_recommendation_engine with a DefaultRecommendationReranker
        composed of PopularityPenaltyPolicy, NoveltyBoostPolicy (both
        reading from the already-resolved book_popularity_repository/
        user_book_interaction_repository), and MMRDiversityPolicy, in that
        order — score-adjusting policies run first, MMR's selection (which
        performs the final, diversity-aware limit-truncation) runs last.
        Re-ranking is implemented as this independent stage precisely so
        HybridRecommendationEngine and every other RecommendationEngine
        stay responsible for candidate generation/fusion only.

        The resolved engines are also exposed directly as fields
        (recommendation_engine, semantic_recommendation_engine,
        hybrid_recommendation_engine, als_recommendation_engine,
        reranked_recommendation_engine) so
        evaluate_recommendation_engine_use_case (stateless; parametrized per
        call, not bound to one engine) can be run against any of them —
        including constructing additional HybridRecommendationEngine or
        RerankedRecommendationEngine instances directly from these same
        building blocks, to compare strategies/policies (see
        scripts/run_demo.py).
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
            else _build_book_embedding_generator()
        )
        semantic_engine = (
            semantic_recommendation_engine
            if semantic_recommendation_engine is not None
            else SemanticRecommendationEngine(embedding_repository, repository)
        )
        interaction_repository = (
            user_book_interaction_repository
            if user_book_interaction_repository is not None
            else _build_user_book_interaction_repository()
        )
        als_engine = (
            als_recommendation_engine
            if als_recommendation_engine is not None
            else _build_als_recommendation_engine(interaction_repository, repository)
        )
        hybrid_engine = (
            hybrid_recommendation_engine
            if hybrid_recommendation_engine is not None
            else HybridRecommendationEngine(
                engine, semantic_engine, als_engine, _build_ranking_strategy()
            )
        )
        reranked_engine = (
            reranked_recommendation_engine
            if reranked_recommendation_engine is not None
            else RerankedRecommendationEngine(
                hybrid_engine, _build_reranker(popularity_repository, interaction_repository)
            )
        )
        return cls(
            book_repository=repository,
            book_popularity_repository=popularity_repository,
            book_embedding_repository=embedding_repository,
            user_book_interaction_repository=interaction_repository,
            recommendation_engine=engine,
            semantic_recommendation_engine=semantic_engine,
            hybrid_recommendation_engine=hybrid_engine,
            als_recommendation_engine=als_engine,
            reranked_recommendation_engine=reranked_engine,
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
            generate_als_recommendation_use_case=GenerateAlsRecommendationUseCase(als_engine),
            generate_reranked_recommendation_use_case=GenerateRerankedRecommendationUseCase(
                reranked_engine
            ),
            evaluate_recommendation_engine_use_case=EvaluateRecommendationEngineUseCase(),
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


def _build_book_embedding_generator() -> BookEmbeddingGenerator:
    config = EmbeddingGeneratorConfig.from_env()
    if config.backend == SENTENCE_TRANSFORMERS_BACKEND:
        # Imported lazily: sentence-transformers is an optional dependency
        # (pyproject.toml's `embeddings` extra), only required when this
        # backend is actually selected.
        from readmatch_ai.infrastructure.sentence_transformer_book_embedding_generator import (
            SentenceTransformerBookEmbeddingGenerator,
        )

        if config.model_name is not None:
            return SentenceTransformerBookEmbeddingGenerator(model_name=config.model_name)
        return SentenceTransformerBookEmbeddingGenerator()
    return DeterministicFakeBookEmbeddingGenerator()


def _build_user_book_interaction_repository() -> UserBookInteractionRepository:
    config = BookRepositoryConfig.from_env()
    if config.backend == POSTGRESQL_BACKEND:
        assert config.database_url is not None  # enforced by BookRepositoryConfig.from_env
        connection = psycopg.connect(config.database_url)
        return PostgreSQLUserBookInteractionRepository(connection)
    return InMemoryUserBookInteractionRepository()


def _build_als_recommendation_engine(
    interaction_repository: UserBookInteractionRepository, book_repository: BookRepository
) -> RecommendationEngine:
    config = AlsModelConfig.from_env()
    store = AlsModelFileStore()
    if config.model_path is not None and store.exists(config.model_path):
        model = store.load(config.model_path)
    else:
        model = train_als_model(interaction_repository.list_all())
        if config.model_path is not None:
            store.save(model, config.model_path)
    return ALSRecommendationEngine(model, book_repository, interaction_repository)


_DEFAULT_HYBRID_WEIGHTS = {POPULARITY_SOURCE: 1 / 3, SEMANTIC_SOURCE: 1 / 3, ALS_SOURCE: 1 / 3}


def _build_ranking_strategy() -> RankingStrategy:
    config = HybridRankingConfig.from_env()
    if config.strategy == RRF_STRATEGY:
        return ReciprocalRankFusionStrategy()
    return WeightedScoreFusionStrategy(dict(_DEFAULT_HYBRID_WEIGHTS))


def _build_reranker(
    popularity_repository: BookPopularityRepository,
    interaction_repository: UserBookInteractionRepository,
) -> RecommendationReranker:
    return DefaultRecommendationReranker(
        [
            PopularityPenaltyPolicy(popularity_repository),
            NoveltyBoostPolicy(interaction_repository),
            MMRDiversityPolicy(),
        ]
    )
