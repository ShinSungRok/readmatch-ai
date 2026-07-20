from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class GenerateSemanticRecommendationUseCase:
    """Retrieves books similar to a given book, delegating to a RecommendationEngine."""

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(self, book_id: str, limit: int) -> RecommendationResult:
        query = RecommendationQuery(limit=limit, book_id=BookId(uuid.UUID(book_id)))
        return self._recommendation_engine.recommend(query)
