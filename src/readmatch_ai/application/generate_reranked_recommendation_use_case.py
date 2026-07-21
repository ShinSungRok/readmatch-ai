from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


class GenerateRerankedRecommendationUseCase:
    """Retrieves re-ranked hybrid recommendations via a RecommendationEngine.

    Mirrors GenerateHybridRecommendationUseCase's shape exactly: the
    RecommendationEngine injected here is expected to be a
    RerankedRecommendationEngine wrapping the Hybrid engine, but this use
    case has no knowledge of that -- it only depends on the
    RecommendationEngine port, same as every other recommendation use case.
    `user_id` is optional here (the personalized API endpoint is what
    enforces "always has a user" by making it a required path parameter);
    `book_id` is optional too, so a source book can still be blended in.
    """

    def __init__(self, recommendation_engine: RecommendationEngine) -> None:
        self._recommendation_engine = recommendation_engine

    def execute(
        self, limit: int, book_id: str | None = None, user_id: str | None = None
    ) -> RecommendationResult:
        query = RecommendationQuery(
            limit=limit,
            book_id=BookId(uuid.UUID(book_id)) if book_id is not None else None,
            user_id=UserId(uuid.UUID(user_id)) if user_id is not None else None,
        )
        return self._recommendation_engine.recommend(query)
