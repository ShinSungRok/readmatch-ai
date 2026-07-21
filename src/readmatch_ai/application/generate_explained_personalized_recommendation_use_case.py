from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.explainer import (
    ExplainedRecommendationItem,
    ExplainedRecommendationResult,
    ExplanationContext,
    RecommendationExplainer,
)
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


class GenerateExplainedPersonalizedRecommendationUseCase:
    """Generates personalized recommendations, then explains the already-produced result.

    Mirrors GenerateRerankedRecommendationUseCase's query-building exactly
    (the injected RecommendationEngine is expected to be the same
    RerankedRecommendationEngine wrapping Hybrid ranking), so the ranked
    items are identical to what the non-explained personalized endpoint
    would return -- no second, independent ranking pass. The injected
    RecommendationExplainer only inspects that already-produced result.
    """

    def __init__(
        self, recommendation_engine: RecommendationEngine, explainer: RecommendationExplainer
    ) -> None:
        self._recommendation_engine = recommendation_engine
        self._explainer = explainer

    def execute(
        self, limit: int, book_id: str | None = None, user_id: str | None = None
    ) -> ExplainedRecommendationResult:
        query_book_id = BookId(uuid.UUID(book_id)) if book_id is not None else None
        query_user_id = UserId(uuid.UUID(user_id)) if user_id is not None else None
        query = RecommendationQuery(limit=limit, book_id=query_book_id, user_id=query_user_id)

        items = self._recommendation_engine.recommend(query).recommendation.items
        context = ExplanationContext(book_id=query_book_id, user_id=query_user_id)
        explanations = self._explainer.explain(items, context)

        explained_items = [
            ExplainedRecommendationItem(item=item, explanation=explanation)
            for item, explanation in zip(items, explanations, strict=True)
        ]
        return ExplainedRecommendationResult(items=explained_items)
