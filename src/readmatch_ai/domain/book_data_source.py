from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PopularLoanBooksQuery:
    """Query parameters for retrieving popular/most-loaned books over a period."""

    start_date: str
    end_date: str


@dataclass(frozen=True)
class PopularLoanBook:
    """Raw external metadata for one popular-loan book record from a data provider.

    Intentionally unvalidated (unlike domain value objects): cleaning and
    mapping into Book is a later import-pipeline concern.
    """

    isbn13: str
    title: str
    author: str
    publisher: str
    category: str
    loan_count: int


class BookDataSource(ABC):
    """Port for retrieving book metadata from an external data provider."""

    @abstractmethod
    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        """Retrieve popular/most-loaned books for the given query."""
