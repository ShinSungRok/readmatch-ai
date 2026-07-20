from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from readmatch_ai.domain.recommendation import RecommendationItem


@dataclass(frozen=True)
class RankingCandidateList:
    """One engine's already-ranked candidates, tagged with a source name for fusion."""

    source: str
    items: list[RecommendationItem]


class RankingStrategy(ABC):
    """Port for fusing multiple engines' ranked candidate lists into one final ranking.

    Pure and algorithm-independent: different fusion algorithms (weighted
    score fusion, reciprocal rank fusion, ...) all implement this same
    contract, so HybridRecommendationEngine can swap strategies via
    configuration without any change to it or to the Application layer.
    """

    @abstractmethod
    def fuse(
        self, candidate_lists: list[RankingCandidateList], limit: int
    ) -> list[RecommendationItem]:
        """Combine candidate lists into one ranked, duplicate-merged, limit-truncated list."""
