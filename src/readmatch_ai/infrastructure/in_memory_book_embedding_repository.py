from __future__ import annotations

import math

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository


class InMemoryBookEmbeddingRepository(BookEmbeddingRepository):
    """In-process BookEmbeddingRepository adapter backed by a dict."""

    def __init__(self) -> None:
        self._embeddings: dict[BookId, BookEmbedding] = {}

    def save(self, embedding: BookEmbedding) -> None:
        self._embeddings[embedding.book_id] = embedding

    def get_by_book_id(self, book_id: BookId) -> BookEmbedding | None:
        return self._embeddings.get(book_id)

    def find_similar(self, vector: tuple[float, ...], limit: int) -> list[BookEmbedding]:
        scored = [
            (self._cosine_similarity(vector, embedding.vector), embedding)
            for embedding in self._embeddings.values()
            if len(embedding.vector) == len(vector)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [embedding for _, embedding in scored[:limit]]

    @staticmethod
    def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
