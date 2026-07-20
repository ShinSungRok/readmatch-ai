from __future__ import annotations

import hashlib

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator

_DEFAULT_MODEL_NAME = "deterministic-fake"
_DEFAULT_DIMENSIONS = 8


class DeterministicFakeBookEmbeddingGenerator(BookEmbeddingGenerator):
    """Deterministic, dependency-free BookEmbeddingGenerator for testing.

    Derives a vector from a SHA-256 digest of the Book's text fields — not a
    real ML model. The same Book text always produces the same vector, and
    different text produces a different vector in practice.
    """

    def __init__(
        self, dimensions: int = _DEFAULT_DIMENSIONS, model_name: str = _DEFAULT_MODEL_NAME
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name

    def generate(self, book: Book) -> BookEmbedding:
        text = f"{book.title.value}|{book.author.value}|{book.category.value}"
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = tuple(digest[i % len(digest)] / 255.0 for i in range(self._dimensions))
        return BookEmbedding(
            book_id=book.id,
            vector=vector,
            model_name=self._model_name,
            dimensions=self._dimensions,
        )
