from __future__ import annotations

from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.reranker import RecommendationReranker, RerankingContext

_DEFAULT_CANDIDATE_MULTIPLIER = 3


class RerankedRecommendationEngine(RecommendationEngine):
    """Wraps any RecommendationEngine with an independent re-ranking stage.

    Over-fetches `query.limit * candidate_multiplier` candidates from the
    inner engine -- re-ranking (in particular MMR-style diversification)
    needs a larger pool to select a diverse limit-sized subset from; a pool
    that's already exactly `limit` long can only be reordered, never
    genuinely diversified -- then delegates to the injected
    RecommendationReranker, which truncates back down to the originally
    requested `query.limit`.

    Implements RecommendationEngine itself (not a special-cased branch
    inside HybridRecommendationEngine or any Application use case), so the
    existing Evaluation Framework, ApplicationContext wiring, and
    Application-layer use cases all work with a reranked pipeline exactly
    as they would with any other engine -- re-ranking stays an independent
    stage, never logic embedded inside a RecommendationEngine's own
    candidate-generation/fusion code.
    """

    def __init__(
        self,
        inner_engine: RecommendationEngine,
        reranker: RecommendationReranker,
        candidate_multiplier: int = _DEFAULT_CANDIDATE_MULTIPLIER,
    ) -> None:
        if candidate_multiplier < 1:
            raise ValueError(f"candidate_multiplier must be >= 1, got {candidate_multiplier!r}")
        self._inner_engine = inner_engine
        self._reranker = reranker
        self._candidate_multiplier = candidate_multiplier

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        candidate_query = RecommendationQuery(
            limit=query.limit * self._candidate_multiplier,
            book_id=query.book_id,
            user_id=query.user_id,
        )
        candidates = self._inner_engine.recommend(candidate_query).recommendation.items
        context = RerankingContext(user_id=query.user_id)
        items = self._reranker.rerank(candidates, query.limit, context)
        return RecommendationResult(recommendation=Recommendation(items=items))
