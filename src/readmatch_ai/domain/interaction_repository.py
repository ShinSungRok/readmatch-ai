from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId


class InteractionRepository(ABC):
    """Port for persisting and retrieving explicit UserInteractions.

    Distinct from UserBookInteractionRepository (the aggregated implicit
    ALS-training signal) -- this stores the typed, explicit interactions
    themselves.
    """

    @abstractmethod
    def record(self, interaction: UserInteraction) -> None:
        """Record an interaction.

        CLICK is event-like: each call adds a new, independent event.
        Every other type is state-like: calling record again for the same
        (user_id, book_id, interaction_type) deterministically replaces the
        prior value -- idempotent when the same interaction is recorded
        repeatedly.
        """

    @abstractmethod
    def clear(self, user_id: UserId, book_id: BookId, interaction_type: InteractionType) -> None:
        """Remove a previously recorded state-like interaction (e.g. un-bookmark).

        A no-op if none was recorded. Not meaningful for an event-like type
        (CLICK); callers should reject that before reaching this port (see
        ClearInteractionUseCase).
        """

    @abstractmethod
    def list_by_user(self, user_id: UserId) -> list[UserInteraction]:
        """Return every interaction currently recorded for a user.

        The latest value per (book, interaction_type) for state-like types,
        plus every individual event for CLICK.
        """
