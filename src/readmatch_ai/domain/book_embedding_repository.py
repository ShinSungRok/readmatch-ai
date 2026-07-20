from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding


class BookEmbeddingRepository(ABC):
    """Port for persisting and retrieving book embeddings.

    Algorithm-independent: any embedding model/version can be stored,
    since BookEmbedding itself carries model_name/dimensions.
    """

    @abstractmethod
    def save(self, embedding: BookEmbedding) -> None:
        """Save (upsert) a book's embedding."""

    @abstractmethod
    def get_by_book_id(self, book_id: BookId) -> BookEmbedding | None:
        """Retrieve a book's embedding, if one exists."""

    @abstractmethod
    def find_similar(self, vector: tuple[float, ...], limit: int) -> list[BookEmbedding]:
        """Return up to `limit` stored embeddings most similar to `vector`, most similar first."""
