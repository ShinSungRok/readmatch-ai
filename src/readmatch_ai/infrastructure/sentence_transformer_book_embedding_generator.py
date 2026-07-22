from __future__ import annotations

from typing import Any

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.embedding_text import build_embedding_text, embedding_content_hash

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MODEL_VERSION = "1"


class SentenceTransformerBookEmbeddingGenerator(BookEmbeddingGenerator):
    """Production BookEmbeddingGenerator backed by a real sentence-transformers model.

    Opt-in via EMBEDDING_GENERATOR_BACKEND=sentence_transformers (see
    config.EmbeddingGeneratorConfig) — DeterministicFakeBookEmbeddingGenerator
    remains the default. The `sentence-transformers` package is an optional
    dependency (pyproject.toml's `embeddings` extra, not installed by
    default); imported lazily here so this module — and the rest of
    Infrastructure — stays importable without it.

    `dimensions` is always derived from the actual encoded vector's length
    (not a separately-reported model property), so a BookEmbedding's
    declared dimensions can never diverge from its vector — the invariant
    BookEmbedding.__post_init__ already enforces before persistence.

    `model_version` (Sprint 48) is a generator-controlled pipeline version,
    independent of `model_name` -- bump it when the embedding text
    construction/normalization changes (see domain.embedding_text) even if
    the underlying model weights don't, so a batch pipeline knows to
    regenerate.
    """

    def __init__(
        self, model_name: str = DEFAULT_MODEL_NAME, model_version: str = DEFAULT_MODEL_VERSION
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name
        self._model_version = model_version
        self._model: Any = SentenceTransformer(model_name)

    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        text = build_embedding_text(book, metadata)
        encoded = self._model.encode(text, normalize_embeddings=True)
        vector = tuple(float(component) for component in encoded)
        return BookEmbedding(
            book_id=book.id,
            vector=vector,
            model_name=self._model_name,
            model_version=self._model_version,
            dimensions=len(vector),
            content_hash=embedding_content_hash(text),
        )
