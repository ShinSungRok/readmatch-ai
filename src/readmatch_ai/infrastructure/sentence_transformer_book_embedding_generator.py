from __future__ import annotations

from typing import Any

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


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
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name
        self._model: Any = SentenceTransformer(model_name)

    def generate(self, book: Book) -> BookEmbedding:
        text = f"{book.title.value}|{book.author.value}|{book.category.value}"
        encoded = self._model.encode(text, normalize_embeddings=True)
        vector = tuple(float(component) for component in encoded)
        return BookEmbedding(
            book_id=book.id,
            vector=vector,
            model_name=self._model_name,
            dimensions=len(vector),
        )
