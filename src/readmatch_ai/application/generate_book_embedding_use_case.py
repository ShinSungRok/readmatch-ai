from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_metadata import BookMetadataRepository
from readmatch_ai.domain.book_repository import BookRepository


class GenerateBookEmbeddingUseCase:
    """Generates a Book's embedding and persists it.

    Resolves the Book via BookRepository first, since
    BookEmbeddingGenerator needs the full Book, not just its id. Also reads
    the Book's optional presentation metadata (Sprint 39) via
    BookMetadataRepository -- passed through to the generator so it can
    include e.g. `description` in the embedded text (Sprint 48); a book
    with no recorded metadata still embeds fine (the generator treats
    `None` the same as "no description"). Saving is an upsert
    (BookEmbeddingRepository.save), so re-running for the same book
    replaces its previous embedding.
    """

    def __init__(
        self,
        book_repository: BookRepository,
        book_embedding_generator: BookEmbeddingGenerator,
        book_embedding_repository: BookEmbeddingRepository,
        book_metadata_repository: BookMetadataRepository,
    ) -> None:
        self._book_repository = book_repository
        self._book_embedding_generator = book_embedding_generator
        self._book_embedding_repository = book_embedding_repository
        self._book_metadata_repository = book_metadata_repository

    def execute(self, book_id: str) -> BookEmbedding | None:
        parsed_book_id = BookId(uuid.UUID(book_id))
        book = self._book_repository.get_by_id(parsed_book_id)
        if book is None:
            return None

        metadata = self._book_metadata_repository.get_by_book_id(parsed_book_id)
        embedding = self._book_embedding_generator.generate(book, metadata)
        self._book_embedding_repository.save(embedding)
        return embedding
