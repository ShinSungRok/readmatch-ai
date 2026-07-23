from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId

MIN_RATING = 1
MAX_RATING = 5


class InteractionType(StrEnum):
    """Every explicit interaction a user can record against a book.

    Distinct from UserBookInteraction (domain.user_book_interaction), which
    stores only the single aggregated implicit signal ALS trains on. This
    is the explicit, typed interaction capability Phase 3 adds.

    VIEW/SEARCH_RESULT_CLICK/RECOMMENDATION_CLICK (Sprint 14) are
    additional event-like behavior-tracking types, distinguishing *where*
    a book was engaged with (a book detail page view, a click from search
    results, a click from a recommendation row) for User Preference
    Profile aggregation -- CLICK's original, undifferentiated meaning is
    unchanged and still accepted, for backward compatibility.
    """

    CLICK = "click"
    LIKE = "like"
    DISLIKE = "dislike"
    BOOKMARK = "bookmark"
    READ = "read"
    RATING = "rating"
    VIEW = "view"
    SEARCH_RESULT_CLICK = "search_result_click"
    RECOMMENDATION_CLICK = "recommendation_click"


# CLICK/VIEW/SEARCH_RESULT_CLICK/RECOMMENDATION_CLICK are event-like: every
# recorded occurrence is an independent event. Every other type is
# state-like: recording again for the same (user, book, type) replaces the
# prior value -- see InteractionRepository.
EVENT_LIKE_INTERACTION_TYPES = frozenset(
    {
        InteractionType.CLICK,
        InteractionType.VIEW,
        InteractionType.SEARCH_RESULT_CLICK,
        InteractionType.RECOMMENDATION_CLICK,
    }
)
STATE_LIKE_INTERACTION_TYPES = frozenset(InteractionType) - EVENT_LIKE_INTERACTION_TYPES


@dataclass(frozen=True)
class UserInteraction:
    """A single explicit user-book interaction.

    `value` carries the rating (MIN_RATING..MAX_RATING) when
    `interaction_type` is RATING; every other type is a presence-only
    signal and must not carry a value.
    """

    user_id: UserId
    book_id: BookId
    interaction_type: InteractionType
    value: int | None = None

    def __post_init__(self) -> None:
        if self.interaction_type == InteractionType.RATING:
            if self.value is None:
                raise ValueError("a rating interaction requires a value")
            if not MIN_RATING <= self.value <= MAX_RATING:
                raise ValueError(
                    f"rating value must be between {MIN_RATING} and {MAX_RATING}, "
                    f"got {self.value!r}"
                )
        elif self.value is not None:
            raise ValueError(
                f"{self.interaction_type.value} interactions must not include a value"
            )
