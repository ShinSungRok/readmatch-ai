from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from readmatch_ai.domain.recommendation import RecommendationItem
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class RerankingContext:
    """Context available to reranking policies beyond the candidate items themselves.

    Deliberately minimal: only who is being served (for a
    personalization-aware policy like novelty boosting), never which engine
    produced the candidates -- coupling reranking to a specific
    RecommendationEngine is exactly what this Sprint's re-ranking stage
    must stay independent of.
    """

    user_id: UserId | None = None


class RerankingPolicy(ABC):
    """Port for one independent, composable re-ranking adjustment.

    Each policy receives the already-ranked candidate list and returns an
    adjusted (re-scored and/or reordered) list of the same items --
    RecommendationReranker is responsible for chaining policies together
    and for the final limit-truncation, not any individual policy, so
    policies can be composed in any order/combination without changing
    each other or the Application layer.
    """

    @abstractmethod
    def apply(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        """Return a re-ranked item list (same items, never fabricated ones)."""


class RecommendationReranker(ABC):
    """Port for the re-ranking stage applied after a RecommendationEngine's candidates.

    Independent of RecommendationEngine by design: a RecommendationEngine's
    responsibility remains candidate generation (and, for
    HybridRecommendationEngine, fusion); re-ranking is invoked as its own
    stage by the caller (see infrastructure.reranked_recommendation_engine),
    never from inside an engine's own recommend() implementation.
    """

    @abstractmethod
    def rerank(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        """Apply this reranker's policies and truncate the result to `limit`."""


class DefaultRecommendationReranker(RecommendationReranker):
    """Applies a configured, ordered sequence of RerankingPolicy instances.

    Each policy runs in turn on the previous policy's output -- adding,
    removing, or reordering policies is a construction-time concern only,
    satisfying "reranking policies must be composable... without changing
    Application logic". The result is always truncated to exactly `limit`
    items (never padded): recommendation count is preserved whenever at
    least `limit` candidates were supplied in the first place -- see
    RerankedRecommendationEngine, which over-fetches from its inner engine
    for exactly this reason.
    """

    def __init__(self, policies: list[RerankingPolicy]) -> None:
        self._policies = list(policies)

    def rerank(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        current = list(items)
        for policy in self._policies:
            current = policy.apply(current, limit, context)
        return current[:limit]
