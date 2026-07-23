from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from readmatch_ai.domain.user import UserId


class PreferenceSignalType(StrEnum):
    """A user behavior signal that is not scoped to a single book.

    Distinct from InteractionType (domain.interaction), which always
    attaches to a book_id -- CATEGORY_INTEREST (the initial onboarding
    category choice) and SEARCH (a submitted query) carry only free text,
    with nothing to reference a specific book.
    """

    CATEGORY_INTEREST = "category_interest"
    SEARCH = "search"


@dataclass(frozen=True)
class UserPreferenceSignal:
    """A single, always event-like (never overwritten) user preference signal.

    `value` is the selected category name for CATEGORY_INTEREST, or the
    submitted query text for SEARCH -- always non-empty, caller-trimmed
    free text, not a controlled vocabulary (mirrors Book's own
    Category/free-text fields; matching a signal's `value` against a
    book's actual category/title is a UserPreferenceProfile concern, not
    this entity's).
    """

    user_id: UserId
    signal_type: PreferenceSignalType
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError(f"{self.signal_type.value} signal requires a non-empty value")
