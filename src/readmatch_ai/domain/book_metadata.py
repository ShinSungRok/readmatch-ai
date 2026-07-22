from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class BookMetadata:
    """Optional, UI-facing metadata for a book, recorded independently of the Book aggregate.

    Every field is optional: a data provider (or the demo dataset) may supply
    only some of them. Missing metadata is a normal, expected state -- not an
    error -- and is handled by the presentation layer (see
    application.book_presentation), not here.
    """

    book_id: BookId
    publisher: str | None = None
    description: str | None = None
    cover_url: str | None = None
    published_date: str | None = None


class BookMetadataRepository(ABC):
    """Port for recording and querying optional book presentation metadata."""

    @abstractmethod
    def record(self, metadata: BookMetadata) -> None:
        """Record (upsert) presentation metadata for a book."""

    @abstractmethod
    def get_by_book_id(self, book_id: BookId) -> BookMetadata | None:
        """Return the recorded metadata for a book, or None if never recorded."""
