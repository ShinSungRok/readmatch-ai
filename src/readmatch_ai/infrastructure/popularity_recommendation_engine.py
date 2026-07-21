from __future__ import annotations

from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation import (
    POPULARITY_SOURCE,
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class PopularityRecommendationEngine(RecommendationEngine):
    """RecommendationEngine ranking books by persisted loan_count.

    Reads only from BookPopularityRepository and BookRepository (both
    already persisted, per Sprint 12) — never calls an external API
    directly. Joins each popularity signal with its Book; a popularity
    entry whose Book can no longer be found is skipped rather than
    failing the whole recommendation.
    """

    def __init__(
        self,
        book_popularity_repository: BookPopularityRepository,
        book_repository: BookRepository,
    ) -> None:
        self._book_popularity_repository = book_popularity_repository
        self._book_repository = book_repository

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        top_popularity = self._book_popularity_repository.top_by_loan_count(query.limit)

        items: list[RecommendationItem] = []
        for popularity in top_popularity:
            book = self._book_repository.get_by_id(popularity.book_id)
            if book is None:
                continue
            items.append(
                RecommendationItem(
                    book=book,
                    score=float(popularity.loan_count),
                    source=POPULARITY_SOURCE,
                    contributing_sources=frozenset({POPULARITY_SOURCE}),
                )
            )

        return RecommendationResult(recommendation=Recommendation(items=items))
