import sys
import types
from typing import Any

import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.sentence_transformer_book_embedding_generator import (
    SentenceTransformerBookEmbeddingGenerator,
)


class _FakeSentenceTransformer:
    """Stands in for sentence_transformers.SentenceTransformer -- no real model download."""

    def __init__(self, model_name: str, *, encoded_vector: list[float]) -> None:
        self.model_name = model_name
        self._encoded_vector = encoded_vector

    def encode(self, text: str, normalize_embeddings: bool = True) -> list[float]:
        return self._encoded_vector


def _install_fake_sentence_transformers_module(
    monkeypatch: pytest.MonkeyPatch, encoded_vector: list[float]
) -> None:
    """Injects a fake sentence_transformers module into sys.modules.

    Works regardless of whether the real (optional, heavy) package is
    actually installed, since SentenceTransformerBookEmbeddingGenerator
    imports it lazily inside __init__ -- the import resolves to this fake.
    """

    def _fake_constructor(model_name: str, **_: Any) -> _FakeSentenceTransformer:
        return _FakeSentenceTransformer(model_name, encoded_vector=encoded_vector)

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _fake_constructor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
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
    encoded_texts: list[str] = []

    class _RecordingSentenceTransformer:
        def __init__(self, model_name: str, **_: object) -> None:
            self.model_name = model_name

        def encode(self, text: str, normalize_embeddings: bool = True) -> list[float]:
            encoded_texts.append(text)
            return [0.0]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _RecordingSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    book = _book()
    generator = SentenceTransformerBookEmbeddingGenerator()
    generator.generate(book, BookMetadata(book_id=book.id, description="A classic."))

    assert "A classic." in encoded_texts[0]
