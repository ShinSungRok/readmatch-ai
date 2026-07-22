from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.domain.interaction import InteractionType


@dataclass(frozen=True)
class LibraryItem:
    """One book in a personal library section, with the interaction that placed it there.

    `value` carries the rating (see UserInteraction) when
    `interaction_type` is RATING, and is None otherwise.
    """

    book: BookPresentation
    interaction_type: InteractionType
    value: int | None


@dataclass(frozen=True)
class LibrarySection:
    """One identified, titled row of LibraryItems (e.g. "Liked")."""

    id: str
    title: str
    items: list[LibraryItem]


@dataclass(frozen=True)
class PersonalLibrary:
    """A user's personal library: zero or more sections.

    Empty (`sections=[]`) for a user with no qualifying interactions -- a
    valid, safe response, not an error. A section with no items is omitted
    entirely rather than included empty, matching HomeFeed's existing
    convention (see application.home_feed).
    """

    sections: list[LibrarySection]
