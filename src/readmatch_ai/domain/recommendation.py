from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import Book


@dataclass(frozen=True)
class RecommendationItem:
    """A single ranked book recommendation, joined with its full Book data.

    `source` identifies which engine/model produced this item (e.g.
    "popularity"), preserved per SYSTEM_ARCHITECTURE.md's ranking rule to
    keep candidate source and score alongside future hybrid ranking.
    """

    book: Book
    score: float
    source: str


@dataclass(frozen=True)
class Recommendation:
    """An ordered list of recommended books (highest-ranked first)."""

    items: list[RecommendationItem]


@dataclass(frozen=True)
class RecommendationQuery:
    """Input to a RecommendationEngine: how many recommendations to return."""

    limit: int


@dataclass(frozen=True)
class RecommendationResult:
    """Output of a RecommendationEngine."""

    recommendation: Recommendation
