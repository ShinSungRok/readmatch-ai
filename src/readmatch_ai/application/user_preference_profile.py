from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class UserPreferenceProfile:
    """A user's aggregated preferences, built entirely from their own recorded
    Interactions and PreferenceSignals -- an Application-layer composition
    (mirrors PersonalLibrary's placement), never a second recommendation
    ranking pass.

    favorite_categories/favorite_authors: categories/authors of the user's
    own positive books (like/bookmark/read/rating>=4), ranked by frequency,
    most-frequent first, ties broken alphabetically for determinism.

    recent_interests: recent categories the user showed interest in --
    onboarding category choices plus categories of recently viewed/clicked
    books -- most-recent-first, deduplicated.

    positive_book_ids/negative_book_ids: every book_id behind the
    favorite/negative signal above (positive: like/bookmark/read/
    rating>=4; negative: dislike/rating<=2), each deduplicated,
    insertion-order.

    recent_search_terms: the user's own submitted search queries,
    most-recent-first, deduplicated (case-insensitive).

    Every field defaults to empty for a user with no qualifying signals
    yet (cold start) -- never fabricated.
    """

    favorite_categories: tuple[str, ...]
    favorite_authors: tuple[str, ...]
    recent_interests: tuple[str, ...]
    positive_book_ids: tuple[BookId, ...]
    negative_book_ids: tuple[BookId, ...]
    recent_search_terms: tuple[str, ...]
