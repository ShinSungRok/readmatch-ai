from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding


class BookEmbeddingGenerator(ABC):
    """Port for generating a semantic embedding from a Book.

    Algorithm-independent: real implementations (e.g. a sentence-transformer
    model) and test doubles both satisfy this same contract.
    """

    @abstractmethod
    def generate(self, book: Book) -> BookEmbedding:
        """Generate an embedding for the given book."""
