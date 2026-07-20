import sys
import types
import uuid
from typing import Any

import pytest

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.popularity_recommendation_engine import (
    PopularityRecommendationEngine,
)
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)


class _FakeRecommendationEngine(RecommendationEngine):
    def __init__(self, result: RecommendationResult) -> None:
        self._result = result

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        return self._result


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


def test_create_exposes_the_resolved_recommendation_engines() -> None:
    context = ApplicationContext.create()

    assert isinstance(context.recommendation_engine, PopularityRecommendationEngine)
    assert isinstance(context.semantic_recommendation_engine, SemanticRecommendationEngine)
    assert isinstance(context.hybrid_recommendation_engine, HybridRecommendationEngine)


def test_evaluate_recommendation_engine_use_case_scores_the_three_wired_engines() -> None:
    context = ApplicationContext.create()
    source = context.register_book_use_case.execute(_valid_input())
    other = context.register_book_use_case.execute(_other_input())
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))
    context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )
    dataset = EvaluationDataset(
        cases=(EvaluationCase(book_id=source.id, relevant_book_ids=frozenset({other.id})),)
    )
    engines = {
        "popularity": context.recommendation_engine,
        "semantic": context.semantic_recommendation_engine,
        "hybrid": context.hybrid_recommendation_engine,
    }

    for name, engine in engines.items():
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

    class _FakeSentenceTransformer:
        def __init__(self, model_name: str, **_: Any) -> None:
            self.model_name = model_name

        def encode(self, text: str, normalize_embeddings: bool = True) -> list[float]:
            return [0.1, 0.2, 0.3]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "sentence_transformers")

    context = ApplicationContext.create()
    book = context.register_book_use_case.execute(_valid_input())

    embedding = context.generate_book_embedding_use_case.execute(str(book.id.value))

    assert embedding is not None
    assert embedding.vector == (0.1, 0.2, 0.3)
    assert embedding.model_name == "sentence-transformers/all-MiniLM-L6-v2"
