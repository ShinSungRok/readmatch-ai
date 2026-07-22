import sys
import types
from collections.abc import Iterator
from typing import Any

import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure import sentence_transformer_book_embedding_generator as st_module
from readmatch_ai.infrastructure.sentence_transformer_book_embedding_generator import (
    DEFAULT_MODEL_NAME,
    EmbeddingDimensionMismatchError,
    SentenceTransformerBookEmbeddingGenerator,
)


@pytest.fixture(autouse=True)
def _clear_model_cache() -> Iterator[None]:
    """Prevents one test's fake model from leaking into another via the
    process-wide _MODEL_CACHE, since tests reuse DEFAULT_MODEL_NAME/other
    shared names with different fake encoders.
    """
    st_module._MODEL_CACHE.clear()
    yield
    st_module._MODEL_CACHE.clear()


class _FakeSentenceTransformer:
    """Stands in for sentence_transformers.SentenceTransformer -- no real model download."""

    def __init__(self, model_name: str, *, encoded_vector: list[float]) -> None:
        self.model_name = model_name
        self._encoded_vector = encoded_vector
        self.encode_call_count = 0

    def encode(
        self, texts: list[str], normalize_embeddings: bool = True
    ) -> list[list[float]]:
        self.encode_call_count += 1
        return [self._encoded_vector for _ in texts]


def _install_fake_sentence_transformers_module(
    monkeypatch: pytest.MonkeyPatch, encoded_vector: list[float]
) -> list[_FakeSentenceTransformer]:
    """Injects a fake sentence_transformers module into sys.modules.

    Works regardless of whether the real (optional, heavy) package is
    actually installed, since SentenceTransformerBookEmbeddingGenerator
    imports it lazily -- the import resolves to this fake. Returns the list
    every fake instance actually constructed gets appended to -- empty
    until a SentenceTransformerBookEmbeddingGenerator is constructed for an
    as-yet-uncached model name, so callers that need to inspect the
    instance (e.g. its encode_call_count) read `created[-1]` *after*
    constructing their generator, not from this function's return value
    directly.
    """
    created: list[_FakeSentenceTransformer] = []

    def _fake_constructor(model_name: str, **_: Any) -> _FakeSentenceTransformer:
        instance = _FakeSentenceTransformer(model_name, encoded_vector=encoded_vector)
        created.append(instance)
        return instance

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _fake_constructor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    return created


def _book(title: str = "Clean Code", isbn: str = "978-3-16-148410-0") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_generate_converts_the_encoded_vector_and_derives_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.1, 0.5, -0.25])
    generator = SentenceTransformerBookEmbeddingGenerator()
    book = _book()

    embedding = generator.generate(book)

    assert embedding.book_id == book.id
    assert embedding.vector == (0.1, 0.5, -0.25)
    assert embedding.dimensions == 3


def test_default_model_is_a_multilingual_model(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])

    generator = SentenceTransformerBookEmbeddingGenerator()
    embedding = generator.generate(_book())

    assert embedding.model_name == DEFAULT_MODEL_NAME
    assert "multilingual" in DEFAULT_MODEL_NAME


def test_generate_uses_the_configured_model_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])

    generator = SentenceTransformerBookEmbeddingGenerator(model_name="custom-model")
    embedding = generator.generate(_book())

    assert embedding.model_name == "custom-model"


def test_generate_is_deterministic_for_the_same_encoded_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.2, 0.4])
    generator = SentenceTransformerBookEmbeddingGenerator()
    book = _book()

    first = generator.generate(book)
    second = generator.generate(book)

    assert first == second


def test_generate_uses_the_configured_model_version(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])

    generator = SentenceTransformerBookEmbeddingGenerator(model_version="2")
    embedding = generator.generate(_book())

    assert embedding.model_version == "2"


def test_generate_sets_a_content_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.1, 0.2])

    embedding = SentenceTransformerBookEmbeddingGenerator().generate(_book())

    assert embedding.content_hash


def test_generate_encodes_the_description_when_metadata_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_texts: list[list[str]] = []

    class _RecordingSentenceTransformer:
        def __init__(self, model_name: str, **_: object) -> None:
            self.model_name = model_name

        def encode(
            self, texts: list[str], normalize_embeddings: bool = True
        ) -> list[list[float]]:
            encoded_texts.append(texts)
            return [[0.0] for _ in texts]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _RecordingSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    book = _book()
    generator = SentenceTransformerBookEmbeddingGenerator()
    generator.generate(book, BookMetadata(book_id=book.id, description="A classic."))

    assert "A classic." in encoded_texts[0][0]


def test_generate_validates_expected_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.1, 0.2, 0.3])

    generator = SentenceTransformerBookEmbeddingGenerator(expected_dimensions=384)

    with pytest.raises(EmbeddingDimensionMismatchError, match="384"):
        generator.generate(_book())


def test_generate_succeeds_when_dimensions_match_expectation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.1, 0.2, 0.3])

    generator = SentenceTransformerBookEmbeddingGenerator(expected_dimensions=3)
    embedding = generator.generate(_book())

    assert embedding.dimensions == 3


# --- generate_batch ---


def test_generate_batch_encodes_every_book_in_a_single_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _install_fake_sentence_transformers_module(monkeypatch, [0.5, 0.5])
    generator = SentenceTransformerBookEmbeddingGenerator()
    books = [_book(title="A", isbn="978-3-16-148410-0"), _book(title="B", isbn="0-306-40615-2")]

    embeddings = generator.generate_batch([(books[0], None), (books[1], None)])

    assert len(embeddings) == 2
    assert {e.book_id for e in embeddings} == {books[0].id, books[1].id}
    assert created[-1].encode_call_count == 1


def test_generate_batch_returns_an_empty_list_for_no_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])
    generator = SentenceTransformerBookEmbeddingGenerator()

    assert generator.generate_batch([]) == []


def test_generate_batch_validates_expected_dimensions_for_every_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.1, 0.2])
    generator = SentenceTransformerBookEmbeddingGenerator(expected_dimensions=384)

    with pytest.raises(EmbeddingDimensionMismatchError):
        generator.generate_batch([(_book(), None)])


# --- model caching ---


def test_two_generators_with_the_same_model_name_share_the_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])

    first = SentenceTransformerBookEmbeddingGenerator(model_name="shared-model")
    second = SentenceTransformerBookEmbeddingGenerator(model_name="shared-model")

    assert first._model is second._model  # noqa: SLF001


def test_generators_with_different_model_names_load_separate_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers_module(monkeypatch, [0.0])

    first = SentenceTransformerBookEmbeddingGenerator(model_name="model-a")
    second = SentenceTransformerBookEmbeddingGenerator(model_name="model-b")

    assert first._model is not second._model  # noqa: SLF001
