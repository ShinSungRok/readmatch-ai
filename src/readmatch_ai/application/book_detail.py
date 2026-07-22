from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.application.home_feed import HomeFeedItem


@dataclass(frozen=True)
class BookDetail:
    """UI-ready detail for a single book: its presentation plus similar books.

    `similar_books` reuses `HomeFeedItem` (presentation + score + source) --
    a similar book is exactly the same shape as a home-feed recommendation,
    so this introduces no new item DTO.
    """

    book: BookPresentation
    similar_books: list[HomeFeedItem]
