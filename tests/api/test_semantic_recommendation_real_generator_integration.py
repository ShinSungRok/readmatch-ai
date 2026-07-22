"""Sprint 51 regression tests: SemanticRecommendationEngine (unchanged since
its original Sprint) integrated end-to-end with a real
SentenceTransformerBookEmbeddingGenerator-shaped adapter -- proving
"integrate real embeddings into the semantic recommender" as a verifiable
claim, not just an architectural assertion. No real model is downloaded
(see tests/infrastructure/test_sentence_transformer_book_embedding_generator.py
for why): a fake `sentence_transformers` module produces controlled,
directionally-meaningful vectors instead, so ranking-by-similarity can be
asserted precisely and deterministically.
"""

import sys
import types
from typing import Any

import pytest
from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.infrastructure import sentence_transformer_book_embedding_generator as st_module

# Deliberately not unit vectors -- proves the engine's own cosine-similarity
# normalization (SemanticRecommendationEngine._cosine_similarity), not just
# vector equality, is what ranks these.
_CLOSE_VECTOR_A = [1.0, 0.1, 0.0]
_CLOSE_VECTOR_B = [0.9, 0.2, 0.0]  # high cosine similarity to A
_FAR_VECTOR_C = [0.0, 0.0, 1.0]  # orthogonal to A


@pytest.fixture(autouse=True)
def _clear_model_cache() -> None:
    st_module._MODEL_CACHE.clear()


def _install_fake_sentence_transformers_module(
    monkeypatch: pytest.MonkeyPatch, vectors_by_text_fragment: dict[str, list[float]]
) -> None:
    """Injects a fake sentence_transformers module keyed by a text fragment.

    Looks up each encoded text's vector by which configured fragment (a
    book title) it *contains*, so the fake stands in for a real model's
    "similar text -> similar vector" behaviour without needing one.
    """

    class _FakeSentenceTransformer:
        def __init__(self, model_name: str, **_: Any) -> None:
            self.model_name = model_name

        def encode(
            self, texts: list[str], normalize_embeddings: bool = True
        ) -> list[list[float]]:
            result = []
            for text in texts:
                match = next(
                    vector
                    for fragment, vector in vectors_by_text_fragment.items()
                    if fragment in text
                )
                result.append(match)
            return result

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)


def _client_with_sentence_transformer_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, ApplicationContext]:
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "sentence_transformers")
    context = ApplicationContext.create()
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    return TestClient(app), context


def test_semantic_recommendations_rank_by_real_generator_similarity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(
        monkeypatch,
        {"Source Book": _CLOSE_VECTOR_A, "Close Book": _CLOSE_VECTOR_B, "Far Book": _FAR_VECTOR_C},
    )
    client, context = _client_with_sentence_transformer_backend(monkeypatch)

    source = context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source Book", "Author", "Fiction")
    )
    close = context.register_book_use_case.execute(
        RegisterBookInput("0-306-40615-2", "Close Book", "Author", "Fiction")
    )
    far = context.register_book_use_case.execute(
        RegisterBookInput("9780132350884", "Far Book", "Author", "Fiction")
    )
    for book in (source, close, far):
        context.generate_book_embedding_use_case.execute(str(book.id.value))

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["book"]["id"] for item in items] == [str(close.id.value), str(far.id.value)]
    assert items[0]["score"] > items[1]["score"]
    assert all(item["source"] == "semantic" for item in items)


def test_semantic_recommendations_response_contract_is_unchanged_for_real_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same response shape as the deterministic-fake path -- switching
    EMBEDDING_GENERATOR_BACKEND changes which vectors are stored, never the
    REST contract.
    """
    _install_fake_sentence_transformers_module(monkeypatch, {"Source": _CLOSE_VECTOR_A})
    client, context = _client_with_sentence_transformer_backend(monkeypatch)
    source = context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source", "Author", "Fiction")
    )
    context.generate_book_embedding_use_case.execute(str(source.id.value))

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    assert set(response.json()) == {"items"}


def test_semantic_recommendations_fallback_is_preserved_for_real_generator_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A book with no embedding yet returns an empty list (200), not an
    error -- the same fallback SemanticRecommendationEngine has always had,
    unaffected by which generator backend is configured, since the engine
    itself is untouched by Phase 4.
    """
    _install_fake_sentence_transformers_module(monkeypatch, {"Source": _CLOSE_VECTOR_A})
    client, context = _client_with_sentence_transformer_backend(monkeypatch)
    source = context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source", "Author", "Fiction")
    )
    # No generate_book_embedding_use_case.execute() call -- source has no embedding.

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_hybrid_recommendations_still_work_with_the_real_generator_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HybridRecommendationEngine (unmodified this Phase) composes whatever
    SemanticRecommendationEngine returns -- proving Sprint 51 required no
    change there either, only the already-generic BookEmbeddingRepository
    plumbing actually being exercised end-to-end.
    """
    _install_fake_sentence_transformers_module(
        monkeypatch, {"Source": _CLOSE_VECTOR_A, "Close": _CLOSE_VECTOR_B}
    )
    client, context = _client_with_sentence_transformer_backend(monkeypatch)
    source = context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source", "Author", "Fiction")
    )
    close = context.register_book_use_case.execute(
        RegisterBookInput("0-306-40615-2", "Close", "Author", "Fiction")
    )
    for book in (source, close):
        context.generate_book_embedding_use_case.execute(str(book.id.value))

    response = client.get(
        "/recommendations/hybrid", params={"book_id": str(source.id.value), "limit": 5}
    )

    assert response.status_code == 200
    item_ids = {item["book"]["id"] for item in response.json()["items"]}
    assert str(close.id.value) in item_ids
    assert str(source.id.value) not in item_ids
