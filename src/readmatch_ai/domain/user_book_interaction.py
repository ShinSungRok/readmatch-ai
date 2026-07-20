from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class UserBookInteraction:
    """An implicit feedback signal: how many times a user interacted with a book.

    `interaction_count` is used directly as the ALS confidence weight (the
    "implicit ALS" approach models confidence from interaction frequency,
    not an explicit star rating).
    """

    user_id: UserId
    book_id: BookId
    interaction_count: int

    def __post_init__(self) -> None:
        if self.interaction_count <= 0:
            raise ValueError("interaction_count must be positive")
