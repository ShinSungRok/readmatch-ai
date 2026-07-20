from __future__ import annotations

from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class GetRecommendationsUseCase:
    """Retrieves book recommendations, delegating to a RecommendationEngine."""

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(self, limit: int) -> RecommendationResult:
        return self._recommendation_engine.recommend(RecommendationQuery(limit=limit))
