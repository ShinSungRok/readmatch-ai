from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    RecommendationItem,
)
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository

POPULARITY_REASON = "popularity"
SEMANTIC_SIMILARITY_REASON = "semantic_similarity"
COLLABORATIVE_BEHAVIOR_REASON = "collaborative_behavior"
NOVELTY_REASON = "novelty"
DIVERSITY_REASON = "diversity"

# Fixed, deterministic ordering applied to every explanation's reasons,
# independent of the order evidence happens to be computed in.
_CANONICAL_REASON_ORDER = (
    POPULARITY_REASON,
    SEMANTIC_SIMILARITY_REASON,
    COLLABORATIVE_BEHAVIOR_REASON,
    NOVELTY_REASON,
    DIVERSITY_REASON,
)

_REASON_MESSAGES = {
    POPULARITY_REASON: "Popular with many readers.",
    SEMANTIC_SIMILARITY_REASON: "Similar in topic to the selected book.",
    COLLABORATIVE_BEHAVIOR_REASON: "Readers with similar interests also engaged with this book.",
    NOVELTY_REASON: "You have not interacted with this book before.",
    DIVERSITY_REASON: "Adds variety to your recommendation list.",
}


@dataclass(frozen=True)
class ExplanationReason:
    """One deterministic, truthful reason a book was recommended.

    `type` is a fixed vocabulary (the *_REASON constants above), not free
    text, so callers can rely on it for machine-readable filtering/rendering
    independent of `message`'s exact wording. No confidence value is
    carried: a RecommendationExplainer only ever reports reasons supported
    by actual evidence, never a fabricated strength.
    """

    type: str
    message: str


@dataclass(frozen=True)
class RecommendationExplanation:
    """The explanation for one recommended book: zero or more ExplanationReasons.

    Zero reasons is valid and expected when evidence is limited -- e.g. a
    popularity-only fallback item recommended to an anonymous/cold-start
    query -- an honestly empty list, never a fabricated one.
    """

    book_id: BookId
    reasons: tuple[ExplanationReason, ...]


@dataclass(frozen=True)
class ExplanationContext:
    """Context a RecommendationExplainer may use beyond the items themselves.

    Mirrors RecommendationQuery's book_id/user_id shape exactly, since an
    explanation describes why *this query's* results appeared.
    """

    book_id: BookId | None = None
    user_id: UserId | None = None


@dataclass(frozen=True)
class ExplainedRecommendationItem:
    """A RecommendationItem paired with its explanation."""

    item: RecommendationItem
    explanation: RecommendationExplanation


@dataclass(frozen=True)
class ExplainedRecommendationResult:
    """An ordered list of ExplainedRecommendationItems (highest-ranked first)."""

    items: list[ExplainedRecommendationItem]


class RecommendationExplainer(ABC):
    """Port for explaining an already-produced ranked result.

    Deliberately explains rather than re-derives the recommendation: an
    implementation must never execute a second, independent ranking/
    recommendation algorithm -- only inspect the RecommendationItems (and
    their `contributing_sources`; see recommendation.py) it's given, plus
    whatever additional evidence its ExplanationContext/injected Ports
    supply. Independent of any concrete RecommendationEngine, FastAPI,
    Pydantic, PostgreSQL, pgvector, or model-internals concerns.
    """

    @abstractmethod
    def explain(
        self, items: list[RecommendationItem], context: ExplanationContext
    ) -> list[RecommendationExplanation]:
        """Return one RecommendationExplanation per item, in the same order as `items`."""


class DefaultRecommendationExplainer(RecommendationExplainer):
    """Derives structured reasons purely from already-available evidence.

    - Popularity / Semantic similarity / Collaborative behaviour: whether
      `item.contributing_sources` includes the corresponding source label
      (POPULARITY_SOURCE/SEMANTIC_SOURCE/ALS_SOURCE) -- i.e. whether that
      signal actually produced this book as a candidate, not merely whether
      it was queried. This is also what naturally gates cold-start cases:
      no `book_id` means Semantic was never queried, so it can never
      contribute, so the semantic reason can never fire, with no separate
      check needed.
    - Novelty: whether the book is absent from the user's own interaction
      history (UserBookInteractionRepository), the same evidence
      NoveltyBoostPolicy itself uses. A no-op (no novelty reason for
      anyone) without a `user_id` in the context.
    - Diversity: whether this book's category is the first occurrence of
      that category within the batch being explained (never claimed for
      the very first item, since there is nothing yet to be "diverse"
      relative to).

    Never runs a second ranking pass and never queries a RecommendationEngine.
    """

    def __init__(self, interaction_repository: UserBookInteractionRepository) -> None:
        self._interaction_repository = interaction_repository

    def explain(
        self, items: list[RecommendationItem], context: ExplanationContext
    ) -> list[RecommendationExplanation]:
        known_book_ids = self._known_book_ids(context)
        seen_categories: set[str] = set()
        explanations: list[RecommendationExplanation] = []
        for item in items:
            reason_types = self._reason_types_for(item, known_book_ids, seen_categories)
            seen_categories.add(item.book.category.value)
            reasons = tuple(
                ExplanationReason(type=reason_type, message=_REASON_MESSAGES[reason_type])
                for reason_type in _CANONICAL_REASON_ORDER
                if reason_type in reason_types
            )
            explanations.append(RecommendationExplanation(book_id=item.book.id, reasons=reasons))
        return explanations

    def _known_book_ids(self, context: ExplanationContext) -> frozenset[BookId] | None:
        if context.user_id is None:
            return None
        return frozenset(
            interaction.book_id
            for interaction in self._interaction_repository.list_by_user(context.user_id)
        )

    @staticmethod
    def _reason_types_for(
        item: RecommendationItem,
        known_book_ids: frozenset[BookId] | None,
        seen_categories: set[str],
    ) -> set[str]:
        reason_types: set[str] = set()
        if POPULARITY_SOURCE in item.contributing_sources:
            reason_types.add(POPULARITY_REASON)
        if SEMANTIC_SOURCE in item.contributing_sources:
            reason_types.add(SEMANTIC_SIMILARITY_REASON)
        if ALS_SOURCE in item.contributing_sources:
            reason_types.add(COLLABORATIVE_BEHAVIOR_REASON)
        if known_book_ids is not None and item.book.id not in known_book_ids:
            reason_types.add(NOVELTY_REASON)
        if seen_categories and item.book.category.value not in seen_categories:
            reason_types.add(DIVERSITY_REASON)
        return reason_types
