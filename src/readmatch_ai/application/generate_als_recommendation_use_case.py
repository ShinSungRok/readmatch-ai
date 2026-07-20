from __future__ import annotations

import uuid

from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


class GenerateAlsRecommendationUseCase:
    """Retrieves collaborative-filtering (ALS) recommendations for a user."""

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(self, user_id: str, limit: int) -> RecommendationResult:
        query = RecommendationQuery(limit=limit, user_id=UserId(uuid.UUID(user_id)))
        return self._recommendation_engine.recommend(query)
