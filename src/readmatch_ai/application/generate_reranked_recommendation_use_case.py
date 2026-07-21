from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class GenerateRerankedRecommendationUseCase:
    """Retrieves re-ranked hybrid recommendations via a RecommendationEngine.

    Mirrors GenerateHybridRecommendationUseCase's shape exactly: the
    RecommendationEngine injected here is expected to be a
    RerankedRecommendationEngine wrapping the Hybrid engine, but this use
    case has no knowledge of that -- it only depends on the
    RecommendationEngine port, same as every other recommendation use case.
    """

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(self, limit: int, book_id: str | None = None) -> RecommendationResult:
        query = RecommendationQuery(
            limit=limit,
            book_id=BookId(uuid.UUID(book_id)) if book_id is not None else None,
        )
        return self._recommendation_engine.recommend(query)
