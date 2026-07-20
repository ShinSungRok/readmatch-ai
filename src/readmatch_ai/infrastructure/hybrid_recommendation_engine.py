from __future__ import annotations

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine

_SOURCE = "hybrid"
_DEFAULT_POPULARITY_WEIGHT = 0.5


class HybridRecommendationEngine(RecommendationEngine):
    """RecommendationEngine combining a popularity engine and a semantic engine.

    Fetches up to `query.limit` candidates from each sub-engine, min-max
    normalizes each engine's own scores independently to [0, 1] (ADR-006:
    "weighted normalized scores form the MVP hybrid ranker"), then combines
    them with a configurable popularity/semantic weight split. A book
    recommended by both engines is merged into a single item whose score is
    the full weighted-sum combination of both signals, not just one side —
    so a book strong in both sources correctly outranks one strong in only
    one.

    Falls back fully to the popularity signal (effective weight 1.0) when no
    source book is given, or the source book has no embedding yet, rather
    than silently scaling every score down by the configured popularity
    weight — matching ADR-004's "Popularity is the baseline and cold-start
    fallback".
    """

    def __init__(
        self,
        popularity_engine: RecommendationEngine,
        semantic_engine: RecommendationEngine,
        popularity_weight: float = _DEFAULT_POPULARITY_WEIGHT,
    ) -> None:
        if not 0.0 <= popularity_weight <= 1.0:
            raise ValueError(f"popularity_weight must be within [0, 1], got {popularity_weight!r}")
        self._popularity_engine = popularity_engine
        self._semantic_engine = semantic_engine
        self._popularity_weight = popularity_weight

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        popularity_items = self._popularity_engine.recommend(query).recommendation.items
        semantic_items = (
            self._semantic_engine.recommend(query).recommendation.items
            if query.book_id is not None
            else []
        )

        popularity_weight, semantic_weight = self._effective_weights(semantic_items)
        normalized_popularity = self._normalize(popularity_items)
        normalized_semantic = self._normalize(semantic_items)

        books: dict[BookId, Book] = {
            item.book.id: item.book for item in (*popularity_items, *semantic_items)
        }
        combined_scores = {
            book_id: (
                popularity_weight * normalized_popularity.get(book_id, 0.0)
                + semantic_weight * normalized_semantic.get(book_id, 0.0)
            )
            for book_id in books
        }

        ranked_book_ids = sorted(
            combined_scores, key=lambda book_id: combined_scores[book_id], reverse=True
        )[: query.limit]
        items = [
            RecommendationItem(book=books[book_id], score=combined_scores[book_id], source=_SOURCE)
            for book_id in ranked_book_ids
        ]
        return RecommendationResult(recommendation=Recommendation(items=items))

    def _effective_weights(self, semantic_items: list[RecommendationItem]) -> tuple[float, float]:
        if not semantic_items:
            return 1.0, 0.0
        return self._popularity_weight, 1.0 - self._popularity_weight

    @staticmethod
    def _normalize(items: list[RecommendationItem]) -> dict[BookId, float]:
        if not items:
            return {}
        scores = [item.score for item in items]
        minimum, maximum = min(scores), max(scores)
        if minimum == maximum:
            return {item.book.id: 1.0 for item in items}
        return {item.book.id: (item.score - minimum) / (maximum - minimum) for item in items}
