from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_metadata import BookMetadata


class BookEmbeddingGenerator(ABC):
    """Port for generating a semantic embedding from a Book.

    Algorithm-independent: real implementations (e.g. a sentence-transformer
    model) and test doubles both satisfy this same contract.

    `metadata` (Sprint 48) is optional presentation metadata (see
    application.book_presentation) -- passed through so an implementation
    can include e.g. `description` in the text it embeds, via
    domain.embedding_text.build_embedding_text. Defaulting to `None` keeps
    this an additive signature change: every existing caller that only has
    a Book still compiles.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model/algorithm name this generator currently stamps onto every BookEmbedding."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """The pipeline version this generator currently stamps onto every BookEmbedding.

        Exposed (Sprint 50) so the batch embedding pipeline can compare a
        stored embedding's (model_name, model_version) against the
        currently-configured generator's, to decide whether a book needs
        regeneration -- without generating anything just to find out.
        """

    @abstractmethod
    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        """Generate an embedding for the given book (and its optional metadata)."""

    def generate_batch(
        self, items: Sequence[tuple[Book, BookMetadata | None]]
    ) -> list[BookEmbedding]:
        """Generate embeddings for many (book, metadata) pairs at once.

        Default implementation: calls generate() once per item -- correct
        for every implementation, but not necessarily fast. A provider that
        can batch more efficiently (e.g. a real model's vectorized encode(),
        which amortizes fixed per-call overhead across many inputs) should
        override this; callers (e.g. the batch embedding pipeline, Sprint
        50) get that efficiency gain transparently, with no change to the
        port's contract or to any caller's code.
        """
        return [self.generate(book, metadata) for book, metadata in items]
