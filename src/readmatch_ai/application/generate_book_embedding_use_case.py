from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_repository import BookRepository


class GenerateBookEmbeddingUseCase:
    """Generates a Book's embedding and persists it.

    Resolves the Book via BookRepository first, since
    BookEmbeddingGenerator needs the full Book, not just its id. Saving is
    an upsert (BookEmbeddingRepository.save), so re-running for the same
    book replaces its previous embedding.
    """

    def __init__(
        self,
        book_repository: BookRepository,
        book_embedding_generator: BookEmbeddingGenerator,
        book_embedding_repository: BookEmbeddingRepository,
    ) -> None:
        self._book_repository = book_repository
        self._book_embedding_generator = book_embedding_generator
        self._book_embedding_repository = book_embedding_repository

    def execute(self, book_id: str) -> BookEmbedding | None:
        book = self._book_repository.get_by_id(BookId(uuid.UUID(book_id)))
        if book is None:
            return None

        embedding = self._book_embedding_generator.generate(book)
        self._book_embedding_repository.save(embedding)
        return embedding
