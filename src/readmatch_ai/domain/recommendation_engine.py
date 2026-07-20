from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult


class RecommendationEngine(ABC):
    """Port for generating book recommendations.

    Independent of any specific recommendation algorithm — Popularity,
    Semantic, and ALS engines (future Sprints) all implement this same
    contract.
    """

    @abstractmethod
    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        """Return recommended books for the given query."""
