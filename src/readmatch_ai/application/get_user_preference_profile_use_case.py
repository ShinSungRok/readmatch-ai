from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable

from readmatch_ai.application.user_preference_profile import UserPreferenceProfile
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.interaction import InteractionType
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.preference_signal import PreferenceSignalType
from readmatch_ai.domain.preference_signal_repository import PreferenceSignalRepository
from readmatch_ai.domain.user import UserId

FAVORITE_CATEGORIES_LIMIT = 5
FAVORITE_AUTHORS_LIMIT = 5
RECENT_INTERESTS_LIMIT = 5
RECENT_SEARCH_TERMS_LIMIT = 5

_POSITIVE_RATING_THRESHOLD = 4
_NEGATIVE_RATING_THRESHOLD = 2

# LIKE/BOOKMARK/READ are always positive; DISLIKE is always negative; RATING
# depends on its value (see the threshold constants above).
_POSITIVE_INTERACTION_TYPES = frozenset(
    {InteractionType.LIKE, InteractionType.BOOKMARK, InteractionType.READ}
)
# The "did the user show interest in this book" signals used for
# recent_interests -- deliberately excludes LIKE/BOOKMARK/etc. (those are
# stronger, favorite-forming signals, already covered by
# favorite_categories/favorite_authors) and CLICK (kept generic/undated,
# see domain.interaction).
_INTEREST_INTERACTION_TYPES = frozenset(
    {
        InteractionType.VIEW,
        InteractionType.SEARCH_RESULT_CLICK,
        InteractionType.RECOMMENDATION_CLICK,
    }
)


class GetUserPreferenceProfileUseCase:
    """Builds a UserPreferenceProfile purely by aggregating a user's own
    already-recorded Interactions and PreferenceSignals.

    No ranking, scoring, or recommendation logic of any kind lives here --
    only counting/ordering of facts the user themselves already generated,
    composed with the existing BookRepository purely to read a book's
    category/author (a presentation/lookup concern, not a recommendation
    one), the same way GetPersonalLibraryUseCase composes
    GetBookPresentationUseCase for a similar reason.
    """

    def __init__(
        self,
        interaction_repository: InteractionRepository,
        preference_signal_repository: PreferenceSignalRepository,
        book_repository: BookRepository,
    ) -> None:
        self._interaction_repository = interaction_repository
        self._preference_signal_repository = preference_signal_repository
        self._book_repository = book_repository

    def execute(self, user_id: str) -> UserPreferenceProfile:
        uid = UserId(uuid.UUID(user_id))
        interactions = self._interaction_repository.list_by_user(uid)
        signals = self._preference_signal_repository.list_by_user(uid)

        positive_book_ids: list[BookId] = []
        negative_book_ids: list[BookId] = []
        # Chronological (oldest first, matching InteractionRepository's own
        # event ordering) -- reversed below to read most-recent-first.
        interest_book_ids: list[BookId] = []
        for interaction in interactions:
            if interaction.interaction_type in _INTEREST_INTERACTION_TYPES:
                interest_book_ids.append(interaction.book_id)
            elif interaction.interaction_type in _POSITIVE_INTERACTION_TYPES:
                positive_book_ids.append(interaction.book_id)
            elif interaction.interaction_type == InteractionType.DISLIKE:
                negative_book_ids.append(interaction.book_id)
            elif interaction.interaction_type == InteractionType.RATING:
                assert interaction.value is not None  # guaranteed by UserInteraction itself
                if interaction.value >= _POSITIVE_RATING_THRESHOLD:
                    positive_book_ids.append(interaction.book_id)
                elif interaction.value <= _NEGATIVE_RATING_THRESHOLD:
                    negative_book_ids.append(interaction.book_id)

        relevant_book_ids = {*positive_book_ids, *negative_book_ids, *interest_book_ids}
        books_by_id = {
            book_id: book
            for book_id in relevant_book_ids
            if (book := self._book_repository.get_by_id(book_id)) is not None
        }

        favorite_categories = _ranked_by_frequency(
            books_by_id[book_id].category.value
            for book_id in positive_book_ids
            if book_id in books_by_id
        )[:FAVORITE_CATEGORIES_LIMIT]
        favorite_authors = _ranked_by_frequency(
            books_by_id[book_id].author.value
            for book_id in positive_book_ids
            if book_id in books_by_id
        )[:FAVORITE_AUTHORS_LIMIT]

        category_interest_choices = [
            signal.value
            for signal in signals
            if signal.signal_type == PreferenceSignalType.CATEGORY_INTEREST
        ]
        interest_categories = [
            books_by_id[book_id].category.value
            for book_id in interest_book_ids
            if book_id in books_by_id
        ]
        # Onboarding category choices happen once, at the very start of a
        # session -- treated as the older tier so a user's later, actual
        # browsing behavior (interest_categories) takes recency priority
        # over their initial pick, without needing a timestamp field on
        # either signal.
        recent_interests = _most_recent_distinct(
            category_interest_choices + interest_categories, RECENT_INTERESTS_LIMIT
        )

        search_terms = [
            signal.value for signal in signals if signal.signal_type == PreferenceSignalType.SEARCH
        ]
        recent_search_terms = _most_recent_distinct(search_terms, RECENT_SEARCH_TERMS_LIMIT)

        return UserPreferenceProfile(
            favorite_categories=tuple(favorite_categories),
            favorite_authors=tuple(favorite_authors),
            recent_interests=tuple(recent_interests),
            positive_book_ids=tuple(_deduplicated(positive_book_ids)),
            negative_book_ids=tuple(_deduplicated(negative_book_ids)),
            recent_search_terms=tuple(recent_search_terms),
        )


def _ranked_by_frequency(values: Iterable[str]) -> list[str]:
    """Most-frequent first; ties broken alphabetically for determinism."""
    counts = Counter(values)
    return [value for value, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _most_recent_distinct(values: list[str], limit: int) -> list[str]:
    """The last `limit` distinct values in `values`, most-recent (last) first.

    Distinctness is case-insensitive (e.g. "Fiction" and "fiction" are the
    same recent interest), but the first-encountered (most recent) casing
    is what's kept.
    """
    seen: set[str] = set()
    result: list[str] = []
    for value in reversed(values):
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) == limit:
            break
    return result


def _deduplicated(book_ids: list[BookId]) -> list[BookId]:
    seen: set[BookId] = set()
    result: list[BookId] = []
    for book_id in book_ids:
        if book_id in seen:
            continue
        seen.add(book_id)
        result.append(book_id)
    return result
