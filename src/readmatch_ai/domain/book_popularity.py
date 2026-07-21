from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class BookPopularity:
    """A book's loan-count signal, recorded independently of the Book aggregate.

    Popularity varies by observation period, so `period_start`/`period_end`
    (matching PopularLoanBooksQuery's date format) are preserved as minimal
    provenance for when this signal was observed.
    """

    book_id: BookId
    loan_count: int
    period_start: str
    period_end: str


class BookPopularityRepository(ABC):
    """Port for recording and querying book popularity (loan count) signals."""

    @abstractmethod
    def record(self, popularity: BookPopularity) -> None:
        """Record (upsert) the loan count for a book."""

    @abstractmethod
    def top_by_loan_count(self, limit: int) -> list[BookPopularity]:
        """Return up to `limit` books ordered by loan_count descending."""

    @abstractmethod
    def get_by_book_id(self, book_id: BookId) -> BookPopularity | None:
        """Return the recorded popularity signal for a book, or None if never recorded."""
