from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_metadata import BookMetadata, BookMetadataRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.embedding_text import build_embedding_text, embedding_content_hash


@dataclass(frozen=True)
class BatchEmbeddingGenerationStats:
    """Deterministic summary of one BatchGenerateBookEmbeddingsUseCase run.

    Book id tuples (not sets) so equality/repr are stable and printable,
    each in the same catalog order the run itself processed books in.
    """

    total_books: int
    generated_book_ids: tuple[str, ...]
    skipped_book_ids: tuple[str, ...]

    @property
    def generated_count(self) -> int:
        return len(self.generated_book_ids)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_book_ids)


class BatchGenerateBookEmbeddingsUseCase:
    """(Re)generates embeddings only for books that actually need it.

    A book needs (re)generation when:
    - it has no stored embedding yet, or
    - its stored embedding's (model_name, model_version) differs from the
      currently-configured generator's -- the model itself, or this
      Sprint's embedding-text/normalization pipeline, changed since it was
      last generated, or
    - its stored embedding's content_hash differs from a freshly computed
      hash of its *current* canonical embedding text -- title, author,
      category, or description changed since it was last generated.

    Every other book is skipped: no model call, no write. Reuses
    BookRepository/BookMetadataRepository/BookEmbeddingGenerator/
    BookEmbeddingRepository exactly as they already exist -- no new
    storage, no new generation algorithm; this only decides *which* books
    to send through the existing GenerateBookEmbeddingUseCase-equivalent
    path, batched via BookEmbeddingGenerator.generate_batch (Sprint 49).

    Deterministic: books are processed in catalog order
    (BookRepository.list_all(), sorted by id so results don't depend on a
    particular adapter's own iteration order), the regeneration decision
    depends only on already-persisted state (never wall-clock time or
    randomness), and generate_batch's own determinism (a given generator
    produces the same vector for the same input every time) carries
    through unchanged.
    """

    def __init__(
        self,
        book_repository: BookRepository,
        book_metadata_repository: BookMetadataRepository,
        book_embedding_generator: BookEmbeddingGenerator,
        book_embedding_repository: BookEmbeddingRepository,
    ) -> None:
        self._book_repository = book_repository
        self._book_metadata_repository = book_metadata_repository
        self._book_embedding_generator = book_embedding_generator
        self._book_embedding_repository = book_embedding_repository

    def execute(self) -> BatchEmbeddingGenerationStats:
        books = sorted(self._book_repository.list_all(), key=lambda book: str(book.id.value))

        to_generate: list[tuple[Book, BookMetadata | None]] = []
        skipped_book_ids: list[str] = []
        for book in books:
            metadata = self._book_metadata_repository.get_by_book_id(book.id)
            if self._needs_regeneration(book, metadata):
                to_generate.append((book, metadata))
            else:
                skipped_book_ids.append(str(book.id.value))

        for embedding in self._book_embedding_generator.generate_batch(to_generate):
            self._book_embedding_repository.save(embedding)

        return BatchEmbeddingGenerationStats(
            total_books=len(books),
            generated_book_ids=tuple(str(book.id.value) for book, _metadata in to_generate),
            skipped_book_ids=tuple(skipped_book_ids),
        )

    def _needs_regeneration(self, book: Book, metadata: BookMetadata | None) -> bool:
        existing = self._book_embedding_repository.get_by_book_id(book.id)
        if existing is None:
            return True
        if (
            existing.model_name != self._book_embedding_generator.model_name
            or existing.model_version != self._book_embedding_generator.model_version
        ):
            return True
        current_content_hash = embedding_content_hash(build_embedding_text(book, metadata))
        return existing.content_hash != current_content_hash
