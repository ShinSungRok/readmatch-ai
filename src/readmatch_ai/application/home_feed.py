from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.book_presentation import BookPresentation


@dataclass(frozen=True)
class HomeFeedItem:
    """A single home-feed recommendation: presentation-ready book data plus its signal."""

    book: BookPresentation
    score: float
    source: str


@dataclass(frozen=True)
class HomeFeedSection:
    """One identified, titled row of HomeFeedItems for the recommendation home."""

    id: str
    title: str
    items: list[HomeFeedItem]


@dataclass(frozen=True)
class HomeFeed:
    """The consolidated recommendation home response: an optional hero plus zero or more sections.

    `hero` and `sections` are both empty/`None` (never an error) when there
    are no books yet -- the same "safe default" handling as every other
    recommendation use case's empty-repository behaviour.
    """

    hero: HomeFeedItem | None
    sections: list[HomeFeedSection]
