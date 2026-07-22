from __future__ import annotations

from dataclasses import dataclass

import psycopg

from readmatch_ai.application.clear_interaction_use_case import ClearInteractionUseCase
from readmatch_ai.application.evaluate_recommendation_engine_use_case import (
    EvaluateRecommendationEngineUseCase,
)
from readmatch_ai.application.generate_als_recommendation_use_case import (
    GenerateAlsRecommendationUseCase,
)
from readmatch_ai.application.generate_book_embedding_use_case import (
    GenerateBookEmbeddingUseCase,
)
from readmatch_ai.application.generate_explained_personalized_recommendation_use_case import (
    GenerateExplainedPersonalizedRecommendationUseCase,
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
from readmatch_ai.application.get_book_detail_use_case import GetBookDetailUseCase
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_home_feed_use_case import GetHomeFeedUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.get_user_interactions_use_case import GetUserInteractionsUseCase
from readmatch_ai.application.health_check_service import HealthCheckService
from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.application.recommendation_metrics_collector import (
    RecommendationMetricsCollector,
)
from readmatch_ai.application.record_interaction_use_case import RecordInteractionUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.config import (
    POSTGRESQL_BACKEND,
    RRF_STRATEGY,
    SENTENCE_TRANSFORMERS_BACKEND,
    AlsModelConfig,
    ApplicationConfiguration,
    BookRepositoryConfig,
    EmbeddingGeneratorConfig,
    HybridRankingConfig,
)
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_metadata import BookMetadataRepository
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.explainer import DefaultRecommendationExplainer, RecommendationExplainer
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.ranking_strategies import (
    ReciprocalRankFusionStrategy,
    WeightedScoreFusionStrategy,
)
from readmatch_ai.domain.ranking_strategy import RankingStrategy
from readmatch_ai.domain.recommendation import ALS_SOURCE, POPULARITY_SOURCE, SEMANTIC_SOURCE
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.recommendation_execution import CompositeRecommendationExecutionObserver
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
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)
from readmatch_ai.infrastructure.logging_recommendation_execution_observer import (
    LoggingRecommendationExecutionObserver,
)
from readmatch_ai.infrastructure.observed_recommendation_engine import ObservedRecommendationEngine
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
from readmatch_ai.infrastructure.postgresql_persistence_runtime_validator import (
    PostgreSQLPersistenceRuntimeValidator,
)
from readmatch_ai.infrastructure.postgresql_user_book_interaction_repository import (
    PostgreSQLUserBookInteractionRepository,
)
from readmatch_ai.infrastructure.reranked_recommendation_engine import (
    RerankedRecommendationEngine,
)
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)
from readmatch_ai.runtime_configuration import (
    COMPOSITION_FAILURE,
    STARTUP_SUCCEEDED,
    ConfigurationValidationResult,
    RuntimeBootstrapValidator,
    RuntimeConfigurationSummary,
    StartupDiagnostic,
    log_startup_diagnostic,
)


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired repositories and use cases."""

    book_repository: BookRepository
    book_popularity_repository: BookPopularityRepository
    book_embedding_repository: BookEmbeddingRepository
    book_metadata_repository: BookMetadataRepository
    explicit_interaction_repository: InteractionRepository
    user_book_interaction_repository: UserBookInteractionRepository
    recommendation_engine: RecommendationEngine
    semantic_recommendation_engine: RecommendationEngine
    hybrid_recommendation_engine: RecommendationEngine
    als_recommendation_engine: RecommendationEngine
    reranked_recommendation_engine: RecommendationEngine
    recommendation_explainer: RecommendationExplainer
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase
    get_book_presentation_use_case: GetBookPresentationUseCase
    get_home_feed_use_case: GetHomeFeedUseCase
    get_book_detail_use_case: GetBookDetailUseCase
    record_interaction_use_case: RecordInteractionUseCase
    clear_interaction_use_case: ClearInteractionUseCase
    get_user_interactions_use_case: GetUserInteractionsUseCase
    get_recommendations_use_case: GetRecommendationsUseCase
    generate_book_embedding_use_case: GenerateBookEmbeddingUseCase
    generate_semantic_recommendation_use_case: GenerateSemanticRecommendationUseCase
    generate_hybrid_recommendation_use_case: GenerateHybridRecommendationUseCase
    generate_als_recommendation_use_case: GenerateAlsRecommendationUseCase
    generate_reranked_recommendation_use_case: GenerateRerankedRecommendationUseCase
    generate_explained_personalized_recommendation_use_case: (
        GenerateExplainedPersonalizedRecommendationUseCase
    )
    evaluate_recommendation_engine_use_case: EvaluateRecommendationEngineUseCase
    health_check_service: HealthCheckService
    readiness_check_service: ReadinessCheckService
    recommendation_metrics_collector: RecommendationMetricsCollector
    runtime_configuration_summary: RuntimeConfigurationSummary

    @classmethod
    def create(
        cls,
        book_repository: BookRepository | None = None,
        book_popularity_repository: BookPopularityRepository | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        book_embedding_repository: BookEmbeddingRepository | None = None,
        book_embedding_generator: BookEmbeddingGenerator | None = None,
        book_metadata_repository: BookMetadataRepository | None = None,
        explicit_interaction_repository: InteractionRepository | None = None,
        semantic_recommendation_engine: RecommendationEngine | None = None,
        hybrid_recommendation_engine: RecommendationEngine | None = None,
        user_book_interaction_repository: UserBookInteractionRepository | None = None,
        als_recommendation_engine: RecommendationEngine | None = None,
        reranked_recommendation_engine: RecommendationEngine | None = None,
        recommendation_explainer: RecommendationExplainer | None = None,
    ) -> ApplicationContext:
        """Validate runtime configuration, then compose the ApplicationContext.

        RuntimeBootstrapValidator.require_valid() (Sprint 32) is the very
        first thing this method does -- a static, deterministic check of the
        current environment's ApplicationConfiguration, independent of which
        parameters this call overrides (mirroring ReadinessCheckService's
        existing env-re-parsing convention). It raises RuntimeBootstrapFailure
        -- carrying every aggregated ConfigurationViolation, not just the
        first -- before any Infrastructure connection (psycopg.connect, ALS
        training, ...) is attempted. Only once configuration is valid does
        `_compose()` (the rest of this method's original body) actually build
        the repositories/engines/use cases; any unexpected failure during
        that phase is logged as a composition_failure StartupDiagnostic and
        re-raised completely unchanged (never swallowed), and a
        startup_succeeded diagnostic is logged once composition completes.
        See `_compose()`'s docstring for the composition rules themselves
        (unchanged from Sprint 31).
        """
        configuration = RuntimeBootstrapValidator().require_valid()
        try:
            context = cls._compose(
                configuration,
                book_repository=book_repository,
                book_popularity_repository=book_popularity_repository,
                recommendation_engine=recommendation_engine,
                book_embedding_repository=book_embedding_repository,
                book_embedding_generator=book_embedding_generator,
                book_metadata_repository=book_metadata_repository,
                explicit_interaction_repository=explicit_interaction_repository,
                semantic_recommendation_engine=semantic_recommendation_engine,
                hybrid_recommendation_engine=hybrid_recommendation_engine,
                user_book_interaction_repository=user_book_interaction_repository,
                als_recommendation_engine=als_recommendation_engine,
                reranked_recommendation_engine=reranked_recommendation_engine,
                recommendation_explainer=recommendation_explainer,
            )
        except Exception as exc:
            log_startup_diagnostic(
                StartupDiagnostic(
                    category=COMPOSITION_FAILURE,
                    message=f"{type(exc).__name__} while composing ApplicationContext",
                )
            )
            raise
        log_startup_diagnostic(
            StartupDiagnostic(
                category=STARTUP_SUCCEEDED, message="ApplicationContext composed successfully"
            )
        )
        return context

    @classmethod
    def _compose(
        cls,
        configuration: ApplicationConfiguration,
        *,
        book_repository: BookRepository | None = None,
        book_popularity_repository: BookPopularityRepository | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        book_embedding_repository: BookEmbeddingRepository | None = None,
        book_embedding_generator: BookEmbeddingGenerator | None = None,
        book_metadata_repository: BookMetadataRepository | None = None,
        explicit_interaction_repository: InteractionRepository | None = None,
        semantic_recommendation_engine: RecommendationEngine | None = None,
        hybrid_recommendation_engine: RecommendationEngine | None = None,
        user_book_interaction_repository: UserBookInteractionRepository | None = None,
        als_recommendation_engine: RecommendationEngine | None = None,
        reranked_recommendation_engine: RecommendationEngine | None = None,
        recommendation_explainer: RecommendationExplainer | None = None,
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

        book_metadata_repository (Sprint 39) always defaults to
        InMemoryBookMetadataRepository -- unlike the other repositories, it
        has no BookRepositoryConfig-driven PostgreSQL backend, since a
        persistence migration is out of this Sprint's scope.
        get_book_presentation_use_case pairs it with `repository` to merge a
        Book with its optional presentation metadata (see
        application.book_presentation) -- a UI concern kept out of the
        recommendation engines/use cases entirely.

        get_home_feed_use_case (Sprint 42) composes the already-built
        popularity_use_case/hybrid_use_case/semantic_use_case (built below,
        before this method's `return`) and book_presentation_use_case into
        one consolidated home-feed response -- the same use case instances
        the individual recommendation endpoints call directly, so a request
        through either path is metered/logged exactly once.

        get_book_detail_use_case (Sprint 43) similarly composes
        book_presentation_use_case with semantic_use_case (the same
        similarity capability, not a new one) into one book-detail response
        (the book plus its similar books).

        explicit_interaction_repository (Sprint 44) always defaults to
        InMemoryInteractionRepository -- like book_metadata_repository, it
        has no BookRepositoryConfig-driven PostgreSQL backend (out of
        Phase 3's scope). Named "explicit" (rather than reusing
        "interaction_repository", which this method's own local variable
        below already uses for user_book_interaction_repository) to avoid
        both a naming collision and any confusion with that unrelated,
        pre-existing port: that one stores only the single aggregated
        implicit signal ALS trains on; this one stores the explicit, typed
        interactions (click/like/dislike/bookmark/read/rating) themselves.
        record_interaction_use_case/clear_interaction_use_case/
        get_user_interactions_use_case each pair it with `repository`
        (record also validates the book exists) or use it directly.

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

        recommendation_explainer defaults to a DefaultRecommendationExplainer
        reading from the already-resolved user_book_interaction_repository.
        generate_explained_personalized_recommendation_use_case pairs it with
        reranked_recommendation_engine: it generates through that same,
        already-resolved engine (identical ranked output to
        generate_reranked_recommendation_use_case) and then explains the
        result -- never a second ranking pass.

        health_check_service/readiness_check_service are always built fresh
        (no override params, matching evaluate_recommendation_engine_use_case's
        stateless pattern): HealthCheckService takes no dependencies at all
        (see its own docstring), and ReadinessCheckService is given
        `repository` plus the resolved recommendation engines (by name) so
        it can probe them without depending on ApplicationContext itself
        (which would invert the dependency direction and create a circular
        import, since this method is what constructs it).

        persistence_runtime_validator (Sprint 33) is a
        PostgreSQLPersistenceRuntimeValidator reusing `repository`'s own
        already-open connection (no second connection is opened) whenever
        `repository` actually is a PostgreSQLBookRepository -- determined by
        `isinstance()` on the already-resolved instance, not the env-derived
        backend name, so an explicit Fake/In-memory override (even with
        BOOK_REPOSITORY_BACKEND=postgresql set in the environment, as in a
        production-shaped-configuration-using-Fakes test) correctly leaves
        it `None`. Passed into ReadinessCheckService, which simply omits its
        persistence_runtime check entirely when `None` -- see that
        service's own docstring.

        recommendation_metrics_collector aggregates
        RecommendationExecutionRecords emitted by every use case that
        actually serves a request -- get_recommendations_use_case,
        generate_semantic_recommendation_use_case,
        generate_hybrid_recommendation_use_case,
        generate_als_recommendation_use_case,
        generate_reranked_recommendation_use_case, and
        generate_explained_personalized_recommendation_use_case are each
        wired to an ObservedRecommendationEngine wrapping their underlying
        engine, reporting to one CompositeRecommendationExecutionObserver
        (this collector, plus a LoggingRecommendationExecutionObserver).
        The `recommendation_engine`/`semantic_recommendation_engine`/etc.
        fields above stay the raw, unwrapped engines -- observability
        wraps only the request-serving path, not the engines used by
        evaluate_recommendation_engine_use_case/quality reporting, so
        neither those fields' concrete types nor offline evaluation runs
        are affected by this Sprint's addition.

        runtime_configuration_summary (Sprint 32) is built from the
        `configuration` this method's caller (`create()`) already validated
        -- never re-read from the environment here -- paired with a
        zero-violation ConfigurationValidationResult, since reaching this
        point already proves validation passed. It is a safe, redacted
        snapshot (adapter categories and the runtime mode, never
        DATABASE_URL or any other secret); see
        runtime_configuration.RuntimeConfigurationSummary's own docstring.
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
        metadata_repository = (
            book_metadata_repository
            if book_metadata_repository is not None
            else InMemoryBookMetadataRepository()
        )
        interaction_repository = (
            user_book_interaction_repository
            if user_book_interaction_repository is not None
            else _build_user_book_interaction_repository()
        )
        explicit_interactions = (
            explicit_interaction_repository
            if explicit_interaction_repository is not None
            else InMemoryInteractionRepository()
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
        explainer = (
            recommendation_explainer
            if recommendation_explainer is not None
            else DefaultRecommendationExplainer(interaction_repository)
        )
        metrics_collector = RecommendationMetricsCollector()
        execution_observer = CompositeRecommendationExecutionObserver(
            [metrics_collector, LoggingRecommendationExecutionObserver()]
        )
        health_check_service = HealthCheckService()
        persistence_runtime_validator = (
            PostgreSQLPersistenceRuntimeValidator(repository.connection)
            if isinstance(repository, PostgreSQLBookRepository)
            else None
        )
        readiness_check_service = ReadinessCheckService(
            repository,
            {
                "popularity": engine,
                "semantic": semantic_engine,
                "als": als_engine,
                "hybrid": hybrid_engine,
                "reranked": reranked_engine,
            },
            persistence_runtime_validator,
        )

        def _observed(
            inner_engine: RecommendationEngine, engine_name: str, recommendation_type: str
        ) -> RecommendationEngine:
            return ObservedRecommendationEngine(
                inner_engine, execution_observer, engine_name, recommendation_type
            )

        popularity_use_case = GetRecommendationsUseCase(
            _observed(engine, "popularity", "popularity")
        )
        hybrid_use_case = GenerateHybridRecommendationUseCase(
            _observed(hybrid_engine, "hybrid", "hybrid")
        )
        semantic_use_case = GenerateSemanticRecommendationUseCase(
            _observed(semantic_engine, "semantic", "semantic")
        )
        book_presentation_use_case = GetBookPresentationUseCase(repository, metadata_repository)

        return cls(
            book_repository=repository,
            book_popularity_repository=popularity_repository,
            book_embedding_repository=embedding_repository,
            book_metadata_repository=metadata_repository,
            explicit_interaction_repository=explicit_interactions,
            user_book_interaction_repository=interaction_repository,
            recommendation_engine=engine,
            semantic_recommendation_engine=semantic_engine,
            hybrid_recommendation_engine=hybrid_engine,
            als_recommendation_engine=als_engine,
            reranked_recommendation_engine=reranked_engine,
            recommendation_explainer=explainer,
            register_book_use_case=RegisterBookUseCase(repository),
            get_book_by_id_use_case=GetBookByIdUseCase(repository),
            get_book_by_isbn_use_case=GetBookByISBNUseCase(repository),
            get_book_presentation_use_case=book_presentation_use_case,
            get_home_feed_use_case=GetHomeFeedUseCase(
                popularity_use_case, hybrid_use_case, semantic_use_case, book_presentation_use_case
            ),
            get_book_detail_use_case=GetBookDetailUseCase(
                book_presentation_use_case, semantic_use_case
            ),
            record_interaction_use_case=RecordInteractionUseCase(explicit_interactions, repository),
            clear_interaction_use_case=ClearInteractionUseCase(explicit_interactions),
            get_user_interactions_use_case=GetUserInteractionsUseCase(explicit_interactions),
            get_recommendations_use_case=popularity_use_case,
            generate_book_embedding_use_case=GenerateBookEmbeddingUseCase(
                repository, embedding_generator, embedding_repository
            ),
            generate_semantic_recommendation_use_case=semantic_use_case,
            generate_hybrid_recommendation_use_case=hybrid_use_case,
            generate_als_recommendation_use_case=GenerateAlsRecommendationUseCase(
                _observed(als_engine, "als", "als")
            ),
            generate_reranked_recommendation_use_case=GenerateRerankedRecommendationUseCase(
                _observed(reranked_engine, "reranked", "personalized")
            ),
            generate_explained_personalized_recommendation_use_case=(
                GenerateExplainedPersonalizedRecommendationUseCase(
                    _observed(reranked_engine, "reranked", "personalized_explained"), explainer
                )
            ),
            evaluate_recommendation_engine_use_case=EvaluateRecommendationEngineUseCase(),
            health_check_service=health_check_service,
            readiness_check_service=readiness_check_service,
            recommendation_metrics_collector=metrics_collector,
            runtime_configuration_summary=RuntimeConfigurationSummary.build(
                configuration, ConfigurationValidationResult(violations=())
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
