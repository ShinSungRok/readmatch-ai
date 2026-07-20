from __future__ import annotations

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
