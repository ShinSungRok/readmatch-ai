import sys
import types
import uuid
from typing import Any

import pytest

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.explainer import (
    DefaultRecommendationExplainer,
    ExplanationContext,
    RecommendationExplainer,
    RecommendationExplanation,
)
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.als_recommendation_engine import ALSRecommendationEngine
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_sync_checkpoint_repository import (
    InMemorySyncCheckpointRepository,
)
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)
from readmatch_ai.infrastructure.popularity_recommendation_engine import (
    PopularityRecommendationEngine,
)
from readmatch_ai.infrastructure.reranked_recommendation_engine import (
    RerankedRecommendationEngine,
)
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)
from readmatch_ai.runtime_configuration import RuntimeBootstrapFailure


class _FakeRecommendationEngine(RecommendationEngine):
    def __init__(self, result: RecommendationResult) -> None:
        self._result = result

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        return self._result


class _FakeRecommendationExplainer(RecommendationExplainer):
    def __init__(self, explanations: list[RecommendationExplanation]) -> None:
        self._explanations = explanations
        self.received_items: list[RecommendationItem] | None = None

    def explain(
        self, items: list[RecommendationItem], context: ExplanationContext
    ) -> list[RecommendationExplanation]:
        self.received_items = items
        return self._explanations


def _valid_input() -> RegisterBookInput:
    return RegisterBookInput(
        isbn="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        category="Software Engineering",
    )


def _other_input() -> RegisterBookInput:
    return RegisterBookInput(
        isbn="0-306-40615-2",
        title="Effective Java",
        author="Joshua Bloch",
        category="Software Engineering",
    )


def _book(isbn: str, title: str) -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def test_create_defaults_to_in_memory_repository() -> None:
    context = ApplicationContext.create()

    assert isinstance(context.book_repository, InMemoryBookRepository)


def test_create_accepts_an_explicit_repository() -> None:
    repository = InMemoryBookRepository()

    context = ApplicationContext.create(book_repository=repository)

    assert context.book_repository is repository


def test_use_cases_share_the_same_repository_instance() -> None:
    context = ApplicationContext.create()

    book = context.register_book_use_case.execute(_valid_input())

    assert context.get_book_by_id_use_case.execute(str(book.id.value)) == book
    assert context.get_book_by_isbn_use_case.execute("978-3-16-148410-0") == book


def test_missing_book_lookups_return_none() -> None:
    context = ApplicationContext.create()

    assert context.get_book_by_id_use_case.execute(str(uuid.uuid4())) is None
    assert context.get_book_by_isbn_use_case.execute("0-306-40615-2") is None


def test_create_calls_are_independent() -> None:
    first_context = ApplicationContext.create()
    second_context = ApplicationContext.create()

    first_context.register_book_use_case.execute(_valid_input())

    assert second_context.get_book_by_isbn_use_case.execute("978-3-16-148410-0") is None


def test_recommendations_reflect_persisted_popularity() -> None:
    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())
    context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    result = context.get_recommendations_use_case.execute(limit=10)

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book == book
    assert result.recommendation.items[0].source == "popularity"


def test_create_accepts_an_explicit_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(recommendation_engine=engine)

    assert context.get_recommendations_use_case.execute(limit=1) is sentinel_result


def test_create_defaults_to_in_memory_embedding_repository() -> None:
    context = ApplicationContext.create()

    assert isinstance(context.book_embedding_repository, InMemoryBookEmbeddingRepository)


def test_generated_embedding_is_retrievable_via_embedding_repository() -> None:
    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())

    embedding = context.generate_book_embedding_use_case.execute(str(book.id.value))

    assert embedding is not None
    assert context.book_embedding_repository.get_by_book_id(book.id) == embedding


def test_generate_book_embedding_returns_none_for_missing_book() -> None:
    context = ApplicationContext.create()

    result = context.generate_book_embedding_use_case.execute(str(uuid.uuid4()))

    assert result is None


def test_semantic_recommendations_reflect_persisted_embeddings() -> None:
    context = ApplicationContext.create()
    source = context.register_book_use_case.execute(_valid_input())
    other = context.register_book_use_case.execute(_other_input())
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))

    result = context.generate_semantic_recommendation_use_case.execute(
        book_id=str(source.id.value), limit=10
    )

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book == other
    assert result.recommendation.items[0].source == "semantic"


def test_create_accepts_an_explicit_semantic_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(semantic_recommendation_engine=engine)

    result = context.generate_semantic_recommendation_use_case.execute(
        book_id=str(uuid.uuid4()), limit=1
    )
    assert result is sentinel_result


def test_hybrid_recommendations_combine_popularity_and_semantic_signals() -> None:
    context = ApplicationContext.create()
    source = context.register_book_use_case.execute(_valid_input())
    other = context.register_book_use_case.execute(_other_input())
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))
    context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    result = context.generate_hybrid_recommendation_use_case.execute(
        limit=10, book_id=str(source.id.value)
    )

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book == other
    assert result.recommendation.items[0].source == "hybrid"


def test_create_accepts_an_explicit_hybrid_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(hybrid_recommendation_engine=engine)

    result = context.generate_hybrid_recommendation_use_case.execute(limit=1)
    assert result is sentinel_result


def test_create_accepts_an_explicit_reranked_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(reranked_recommendation_engine=engine)

    result = context.generate_reranked_recommendation_use_case.execute(limit=1)
    assert result == []


def test_reranked_recommendations_preserve_the_requested_count_and_exclude_the_source_book() -> (
    None
):
    context = ApplicationContext.create()
    isbns = [
        "978-3-16-148410-0",
        "0-306-40615-2",
        "9780132350884",
        "978-0-13-468599-1",
        "978-0-596-00712-6",
        "9791165341909",
    ]
    books = [
        context.register_book_use_case.execute(
            RegisterBookInput(isbn=isbn, title=f"Title {i}", author="Author", category="Category")
        )
        for i, isbn in enumerate(isbns)
    ]
    for book in books:
        context.generate_book_embedding_use_case.execute(str(book.id.value))
    source = books[0]

    result = context.generate_reranked_recommendation_use_case.execute(
        limit=3, book_id=str(source.id.value)
    )

    assert len(result) == 3
    assert all(item.book.id != str(source.id.value) for item in result)


def test_create_exposes_the_resolved_recommendation_engines() -> None:
    context = ApplicationContext.create()

    assert isinstance(context.recommendation_engine, PopularityRecommendationEngine)
    assert isinstance(context.semantic_recommendation_engine, SemanticRecommendationEngine)
    assert isinstance(context.hybrid_recommendation_engine, HybridRecommendationEngine)
    assert isinstance(context.als_recommendation_engine, ALSRecommendationEngine)
    assert isinstance(context.reranked_recommendation_engine, RerankedRecommendationEngine)
    assert isinstance(context.recommendation_explainer, DefaultRecommendationExplainer)


def test_create_accepts_an_explicit_recommendation_explainer() -> None:
    explanation = RecommendationExplanation(book_id=BookId.generate(), reasons=())
    explainer = _FakeRecommendationExplainer([explanation])

    context = ApplicationContext.create(recommendation_explainer=explainer)

    assert context.recommendation_explainer is explainer


def test_explained_personalized_recommendations_use_the_configured_explainer() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)
    explainer = _FakeRecommendationExplainer([])

    context = ApplicationContext.create(
        reranked_recommendation_engine=engine, recommendation_explainer=explainer
    )

    result = context.generate_explained_personalized_recommendation_use_case.execute(
        limit=1, user_id=str(UserId.generate().value)
    )
    assert result.items == []
    assert explainer.received_items == []


def test_explained_personalized_recommendations_include_evidence_based_reasons() -> None:
    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())
    context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=50, period_start="2024-01-01", period_end="2024-01-31")
    )

    result = context.generate_explained_personalized_recommendation_use_case.execute(
        limit=10, user_id=str(UserId.generate().value)
    )

    assert len(result.items) == 1
    assert result.items[0].book.id == str(book.id.value)
    reason_types = [reason.type for reason in result.items[0].reasons]
    assert "popularity" in reason_types
    assert "novelty" in reason_types


def test_create_defaults_to_in_memory_user_book_interaction_repository() -> None:
    context = ApplicationContext.create()

    assert isinstance(
        context.user_book_interaction_repository, InMemoryUserBookInteractionRepository
    )


def test_create_accepts_an_explicit_user_book_interaction_repository() -> None:
    repository = InMemoryUserBookInteractionRepository()

    context = ApplicationContext.create(user_book_interaction_repository=repository)

    assert context.user_book_interaction_repository is repository


def test_create_accepts_an_explicit_als_recommendation_engine() -> None:
    sentinel_result = RecommendationResult(Recommendation(items=[]))
    engine = _FakeRecommendationEngine(sentinel_result)

    context = ApplicationContext.create(als_recommendation_engine=engine)

    result = context.generate_als_recommendation_use_case.execute(
        user_id=str(uuid.uuid4()), limit=1
    )
    assert result is sentinel_result


def test_als_recommendations_exclude_already_interacted_books() -> None:
    """ALS trains once at ApplicationContext.create() time from whatever
    interactions exist then, so interactions must be recorded beforehand —
    recording them after context creation would not retroactively retrain
    this ALS engine instance (see application_context.py's docstring).
    """
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    liked = _book("978-3-16-148410-0", "Liked")
    unseen = _book("0-306-40615-2", "Unseen")
    book_repository.add(liked)
    book_repository.add(unseen)

    user, other_user = UserId.generate(), UserId.generate()
    interaction_repository.record(UserBookInteraction(user, liked.id, interaction_count=5))
    interaction_repository.record(UserBookInteraction(other_user, liked.id, interaction_count=4))
    interaction_repository.record(UserBookInteraction(other_user, unseen.id, interaction_count=3))

    context = ApplicationContext.create(
        book_repository=book_repository, user_book_interaction_repository=interaction_repository
    )

    result = context.generate_als_recommendation_use_case.execute(
        user_id=str(user.value), limit=10
    )

    recommended_ids = {item.book.id for item in result.recommendation.items}
    assert liked.id not in recommended_ids
    assert all(item.source == "als" for item in result.recommendation.items)


def test_evaluate_recommendation_engine_use_case_scores_the_five_wired_engines() -> None:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    source = _book("978-3-16-148410-0", "Source")
    other = _book("0-306-40615-2", "Other")
    book_repository.add(source)
    book_repository.add(other)

    user, other_user = UserId.generate(), UserId.generate()
    interaction_repository.record(UserBookInteraction(user, source.id, interaction_count=1))
    interaction_repository.record(UserBookInteraction(other_user, source.id, interaction_count=5))
    interaction_repository.record(UserBookInteraction(other_user, other.id, interaction_count=5))

    context = ApplicationContext.create(
        book_repository=book_repository, user_book_interaction_repository=interaction_repository
    )
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))
    context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    book_based_dataset = EvaluationDataset(
        cases=(EvaluationCase(book_id=source.id, relevant_book_ids=frozenset({other.id})),)
    )
    # A single eligible candidate (`other`; `source` is excluded as already
    # interacted) makes ALS's ranking unambiguous too, and leaves the
    # reranked engine nothing to reorder among, so the same precise
    # assertions below hold for all five engines.
    user_based_dataset = EvaluationDataset(
        cases=(EvaluationCase(user_id=user, relevant_book_ids=frozenset({other.id})),)
    )
    engines_and_datasets = {
        "popularity": (context.recommendation_engine, book_based_dataset),
        "semantic": (context.semantic_recommendation_engine, book_based_dataset),
        "hybrid": (context.hybrid_recommendation_engine, book_based_dataset),
        "als": (context.als_recommendation_engine, user_based_dataset),
        "reranked": (context.reranked_recommendation_engine, book_based_dataset),
    }

    for name, (engine, dataset) in engines_and_datasets.items():
        result = context.evaluate_recommendation_engine_use_case.execute(
            engine, name, dataset, k=10
        )

        assert result.engine_name == name
        assert result.k == 10
        assert result.case_count == 1
        assert result.precision_at_k == pytest.approx(1 / 10)
        assert result.recall_at_k == pytest.approx(1.0)
        assert result.map_at_k == pytest.approx(1.0)
        assert result.ndcg_at_k == pytest.approx(1.0)
        assert result.hit_rate_at_k == pytest.approx(1.0)
        assert result.diversity_at_k == pytest.approx(1.0)


def test_create_defaults_to_deterministic_fake_embedding_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EMBEDDING_GENERATOR_BACKEND", raising=False)
    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())

    embedding = context.generate_book_embedding_use_case.execute(str(book.id.value))

    assert embedding is not None
    assert embedding.model_name == "deterministic-fake"


def test_create_uses_sentence_transformer_generator_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Config-driven provider selection through the Composition Root.

    Injects a fake sentence_transformers module (sys.modules) so this proves
    the wiring path (env var -> _build_book_embedding_generator ->
    SentenceTransformerBookEmbeddingGenerator) without needing the real,
    heavy, optional dependency installed or a model download.
    """

    from readmatch_ai.infrastructure import (
        sentence_transformer_book_embedding_generator as st_module,
    )

    class _FakeSentenceTransformer:
        def __init__(self, model_name: str, **_: Any) -> None:
            self.model_name = model_name

        def encode(
            self, texts: list[str], normalize_embeddings: bool = True
        ) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "sentence_transformers")
    st_module._MODEL_CACHE.clear()  # avoid leaking another test's cached fake model

    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())

    embedding = context.generate_book_embedding_use_case.execute(str(book.id.value))

    assert embedding is not None
    assert embedding.vector == (0.1, 0.2, 0.3)
    assert embedding.model_name == st_module.DEFAULT_MODEL_NAME

    st_module._MODEL_CACHE.clear()  # avoid leaking this test's fake model to later tests


# --- Sprint 31: production observability ---


def test_create_wires_a_healthy_health_check_service() -> None:
    context = ApplicationContext.create()

    status = context.health_check_service.check()

    assert status.healthy is True


def test_create_wires_a_ready_readiness_check_service_for_a_fresh_in_memory_context() -> None:
    context = ApplicationContext.create()

    status = context.readiness_check_service.check()

    assert status.ready is True


def test_recommendation_metrics_collector_starts_empty() -> None:
    context = ApplicationContext.create()

    snapshot = context.recommendation_metrics_collector.snapshot()

    assert snapshot.request_count == 0


def test_get_recommendations_use_case_reports_execution_to_the_metrics_collector() -> None:
    context = ApplicationContext.create()
    context.register_book_use_case.execute(_valid_input())

    context.get_recommendations_use_case.execute(limit=5)

    snapshot = context.recommendation_metrics_collector.snapshot()
    assert snapshot.request_count == 1
    assert snapshot.success_count == 1
    assert snapshot.engine_usage_counts == {"popularity": 1}


def test_multiple_use_cases_are_each_tracked_under_their_own_engine_name() -> None:
    context = ApplicationContext.create()

    context.get_recommendations_use_case.execute(limit=5)
    context.generate_hybrid_recommendation_use_case.execute(limit=5)

    snapshot = context.recommendation_metrics_collector.snapshot()
    assert snapshot.request_count == 2
    assert snapshot.engine_usage_counts == {"popularity": 1, "hybrid": 1}


def test_the_raw_recommendation_engine_field_remains_unwrapped() -> None:
    """Observability wraps only the engines injected into the request-serving
    use cases (see ApplicationContext.create()'s docstring) -- the exposed
    `recommendation_engine`/etc. fields, used by
    evaluate_recommendation_engine_use_case, must keep their original
    concrete type so quality-report/evaluation behaviour is unaffected.
    """
    context = ApplicationContext.create()

    assert isinstance(context.recommendation_engine, PopularityRecommendationEngine)
    assert isinstance(context.hybrid_recommendation_engine, HybridRecommendationEngine)


def test_repeated_recommendation_requests_deterministically_accumulate_metrics() -> None:
    context = ApplicationContext.create()

    for _ in range(3):
        context.get_recommendations_use_case.execute(limit=5)

    snapshot = context.recommendation_metrics_collector.snapshot()
    assert snapshot.request_count == 3
    assert snapshot.success_count == 3
    assert snapshot.engine_usage_counts == {"popularity": 3}


# --- Sprint 32: operational configuration and runtime hardening ---


def test_create_exposes_a_valid_runtime_configuration_summary_by_default() -> None:
    context = ApplicationContext.create()

    summary = context.runtime_configuration_summary

    assert summary.mode == "development"
    assert summary.book_repository_backend == "in_memory"
    assert summary.configuration_valid is True


def test_create_raises_runtime_bootstrap_failure_for_production_mode_with_in_memory_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")

    with pytest.raises(RuntimeBootstrapFailure) as exc_info:
        ApplicationContext.create()

    assert any(
        v.code == "production_mode_requires_persistent_repository"
        for v in exc_info.value.result.violations
    )


def test_create_never_attempts_a_database_connection_when_static_configuration_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail-fast must happen before any Infrastructure connection --
    poisons psycopg.connect so this test fails loudly (not just silently
    passes) if RuntimeBootstrapValidator.require_valid() is ever bypassed
    or moved after composition begins.
    """
    monkeypatch.setenv("APPLICATION_MODE", "production")

    def _poisoned_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("psycopg.connect must not be called when configuration is invalid")

    monkeypatch.setattr("psycopg.connect", _poisoned_connect)

    with pytest.raises(RuntimeBootstrapFailure):
        ApplicationContext.create()


def test_create_rejects_an_unknown_runtime_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "staging")

    with pytest.raises(RuntimeBootstrapFailure) as exc_info:
        ApplicationContext.create()

    assert any(v.code == "unknown_runtime_mode" for v in exc_info.value.result.violations)


def test_create_supports_a_valid_test_mode_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "test")

    context = ApplicationContext.create()

    assert context.runtime_configuration_summary.mode == "test"
    assert context.runtime_configuration_summary.configuration_valid is True


def test_create_supports_a_production_shaped_configuration_using_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A production-mode, persistent-backend-selected environment (so
    static validation passes exactly as it would for a real deployment)
    while every actual repository/engine is still overridden with
    deterministic in-memory Fakes -- no real PostgreSQL connection is ever
    attempted, since every override parameter that would otherwise trigger
    one is supplied explicitly.
    """
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    fake_repository = InMemoryBookRepository()
    context = ApplicationContext.create(
        book_repository=fake_repository,
        book_popularity_repository=InMemoryBookPopularityRepository(),
        book_embedding_repository=InMemoryBookEmbeddingRepository(),
        user_book_interaction_repository=InMemoryUserBookInteractionRepository(),
        sync_checkpoint_repository=InMemorySyncCheckpointRepository(),
    )

    assert context.book_repository is fake_repository
    assert context.runtime_configuration_summary.mode == "production"
    assert context.runtime_configuration_summary.book_repository_backend == "postgresql"
    assert context.runtime_configuration_summary.configuration_valid is True


def test_runtime_configuration_summary_never_exposes_the_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-pass@host/db")

    context = ApplicationContext.create(
        book_repository=InMemoryBookRepository(),
        book_popularity_repository=InMemoryBookPopularityRepository(),
        book_embedding_repository=InMemoryBookEmbeddingRepository(),
        user_book_interaction_repository=InMemoryUserBookInteractionRepository(),
        sync_checkpoint_repository=InMemorySyncCheckpointRepository(),
    )

    for value in context.runtime_configuration_summary.__dict__.values():
        assert "secret-user" not in str(value)
        assert "secret-pass" not in str(value)


def test_create_is_deterministic_across_repeated_calls_with_the_same_environment() -> None:
    first = ApplicationContext.create()
    second = ApplicationContext.create()

    assert first.runtime_configuration_summary == second.runtime_configuration_summary


# --- Sprint 33: production persistence and vector runtime integration validation ---


def test_default_in_memory_composition_has_no_persistence_runtime_check() -> None:
    context = ApplicationContext.create()

    status = context.readiness_check_service.check()

    check_names = {check.name for check in status.checks}
    assert "persistence_runtime" not in check_names


def test_a_fake_repository_override_never_wires_a_persistence_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors Sprint 32's production-shaped-configuration-using-Fakes
    precedent: even with BOOK_REPOSITORY_BACKEND=postgresql set in the
    environment, an explicit non-PostgreSQL override must never trigger
    persistence runtime validation -- there is nothing real to validate,
    and no PostgreSQL connection should ever be attempted for a Fake.
    """
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    context = ApplicationContext.create(
        book_repository=InMemoryBookRepository(),
        book_popularity_repository=InMemoryBookPopularityRepository(),
        book_embedding_repository=InMemoryBookEmbeddingRepository(),
        user_book_interaction_repository=InMemoryUserBookInteractionRepository(),
        sync_checkpoint_repository=InMemorySyncCheckpointRepository(),
    )

    status = context.readiness_check_service.check()

    check_names = {check.name for check in status.checks}
    assert "persistence_runtime" not in check_names
