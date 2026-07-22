from __future__ import annotations

from abc import ABC, abstractmethod

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

    @abstractmethod
    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        """Generate an embedding for the given book (and its optional metadata)."""
