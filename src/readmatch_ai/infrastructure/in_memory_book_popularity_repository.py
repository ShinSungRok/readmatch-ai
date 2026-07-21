from __future__ import annotations

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_popularity import BookPopularity, BookPopularityRepository


class InMemoryBookPopularityRepository(BookPopularityRepository):
    """In-process BookPopularityRepository adapter backed by a dict."""

    def __init__(self) -> None:
        self._popularity: dict[BookId, BookPopularity] = {}

    def record(self, popularity: BookPopularity) -> None:
        self._popularity[popularity.book_id] = popularity

    def top_by_loan_count(self, limit: int) -> list[BookPopularity]:
        ranked = sorted(
            self._popularity.values(), key=lambda p: p.loan_count, reverse=True
        )
        return ranked[:limit]

    def get_by_book_id(self, book_id: BookId) -> BookPopularity | None:
        return self._popularity.get(book_id)
