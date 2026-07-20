from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.user import UserId


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
