from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction


class UserBookInteractionRepository(ABC):
    """Port for persisting and retrieving implicit user-book interaction signals.

    `list_all` is the training set collaborative filtering (e.g. ALS) reads
    from; algorithm-independent, like the other repository ports.
    """

    @abstractmethod
    def record(self, interaction: UserBookInteraction) -> None:
        """Save (upsert) a user's interaction signal for a book."""

    @abstractmethod
    def list_all(self) -> list[UserBookInteraction]:
        """Return every stored interaction."""

    @abstractmethod
    def list_by_user(self, user_id: UserId) -> list[UserBookInteraction]:
        """Return all interactions recorded for a given user."""
