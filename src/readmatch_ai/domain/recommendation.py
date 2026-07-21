from __future__ import annotations

from dataclasses import dataclass, field

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.user import UserId

# Recommendation-source identifiers, shared by every engine/fusion strategy
# that produces or merges RecommendationItems (HybridRecommendationEngine,
# the RankingStrategy implementations, RecommendationExplainer) -- kept in
# Domain, not Infrastructure, since Domain code (e.g. the explainer) needs
# to reference them without depending on a concrete engine's module.
POPULARITY_SOURCE = "popularity"
SEMANTIC_SOURCE = "semantic"
ALS_SOURCE = "als"
HYBRID_SOURCE = "hybrid"


@dataclass(frozen=True)
class RecommendationItem:
    """A single ranked book recommendation, joined with its full Book data.

    `source` identifies which engine/model produced this item (e.g.
    "popularity"), preserved per SYSTEM_ARCHITECTURE.md's ranking rule to
    keep candidate source and score alongside future hybrid ranking.

    `contributing_sources` records which of the underlying single-signal
    sources (POPULARITY_SOURCE/SEMANTIC_SOURCE/ALS_SOURCE) actually produced
    this book as a candidate -- distinct from `source`, which collapses to
    HYBRID_SOURCE for every item once HybridRecommendationEngine fuses
    multiple sources into one ranking. Without this, a fused item's original
    per-signal provenance would be unrecoverable, which RecommendationExplainer
    needs to give truthful, evidence-based explanations. Defaults to an
    empty frozenset (unknown/not tracked) so existing call sites/tests that
    construct a RecommendationItem without it are unaffected.
    """

    book: Book
    score: float
    source: str
    contributing_sources: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Recommendation:
    """An ordered list of recommended books (highest-ranked first)."""

    items: list[RecommendationItem]


@dataclass(frozen=True)
class RecommendationQuery:
    """Input to a RecommendationEngine: how many recommendations to return.

    `book_id` is the optional source book for engines that recommend "similar
    to this book" (e.g. Semantic); `user_id` is the optional user for
    engines that personalize from a user's own history (e.g. ALS
    collaborative filtering). Engines that don't need a given field ignore
    it (e.g. Popularity ignores both).
    """

    limit: int
    book_id: BookId | None = None
    user_id: UserId | None = None


@dataclass(frozen=True)
class RecommendationResult:
    """Output of a RecommendationEngine."""

    recommendation: Recommendation
