from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class GenerateHybridRecommendationUseCase:
    """Retrieves hybrid (popularity + semantic) recommendations via a RecommendationEngine.

    `book_id` is optional: omitting it (e.g. a homepage with no source book)
    degrades gracefully to the popularity signal, handled by the underlying
    HybridRecommendationEngine rather than this use case.
    """

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(self, limit: int, book_id: str | None = None) -> RecommendationResult:
        query = RecommendationQuery(
            limit=limit,
            book_id=BookId(uuid.UUID(book_id)) if book_id is not None else None,
        )
        return self._recommendation_engine.recommend(query)
