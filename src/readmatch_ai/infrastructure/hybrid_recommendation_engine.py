from __future__ import annotations

from readmatch_ai.domain.ranking_strategy import RankingCandidateList, RankingStrategy
from readmatch_ai.domain.recommendation import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    Recommendation,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class HybridRecommendationEngine(RecommendationEngine):
    """RecommendationEngine combining Popularity, Semantic, and ALS candidates.

    Fetches up to `query.limit` candidates from each available sub-engine —
    Semantic only if `query.book_id` is set, ALS only if `query.user_id` is
    set, matching each engine's own required-input contract — and delegates
    all fusion (normalization, weighting/ranking, duplicate merging,
    truncation) to the injected RankingStrategy. Swapping fusion algorithms
    (e.g. weighted score fusion vs. reciprocal rank fusion) requires only a
    different RankingStrategy at composition time; this class and the
    Application layer are unaffected either way.
    """

    def __init__(
        self,
        popularity_engine: RecommendationEngine,
        semantic_engine: RecommendationEngine,
        als_engine: RecommendationEngine,
        ranking_strategy: RankingStrategy,
    ) -> None:
        self._popularity_engine = popularity_engine
        self._semantic_engine = semantic_engine
        self._als_engine = als_engine
        self._ranking_strategy = ranking_strategy

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        candidate_lists = [
            RankingCandidateList(
                source=POPULARITY_SOURCE,
                items=self._popularity_engine.recommend(query).recommendation.items,
            )
        ]
        if query.book_id is not None:
            candidate_lists.append(
                RankingCandidateList(
                    source=SEMANTIC_SOURCE,
                    items=self._semantic_engine.recommend(query).recommendation.items,
                )
            )
        if query.user_id is not None:
            candidate_lists.append(
                RankingCandidateList(
                    source=ALS_SOURCE,
                    items=self._als_engine.recommend(query).recommendation.items,
                )
            )

        items = self._ranking_strategy.fuse(candidate_lists, query.limit)
        return RecommendationResult(recommendation=Recommendation(items=items))
