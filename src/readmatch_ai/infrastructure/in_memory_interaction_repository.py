from __future__ import annotations

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import (
    EVENT_LIKE_INTERACTION_TYPES,
    InteractionType,
    UserInteraction,
)
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.user import UserId

_StateKey = tuple[UserId, BookId, InteractionType]


class InMemoryInteractionRepository(InteractionRepository):
    """In-process InteractionRepository adapter.

    State-like interactions are dict-backed (last write wins per
    (user, book, type), making repeated record() calls idempotent). CLICK
    events are appended to an independent list, since each is its own
    occurrence rather than a state to overwrite.
    """

    def __init__(self) -> None:
        self._state: dict[_StateKey, UserInteraction] = {}
        self._events: list[UserInteraction] = []

    def record(self, interaction: UserInteraction) -> None:
        if interaction.interaction_type in EVENT_LIKE_INTERACTION_TYPES:
            self._events.append(interaction)
            return
        key = (interaction.user_id, interaction.book_id, interaction.interaction_type)
        self._state[key] = interaction

    def clear(self, user_id: UserId, book_id: BookId, interaction_type: InteractionType) -> None:
        self._state.pop((user_id, book_id, interaction_type), None)

    def list_by_user(self, user_id: UserId) -> list[UserInteraction]:
        state_items = [
            interaction for key, interaction in self._state.items() if key[0] == user_id
        ]
        event_items = [
            interaction for interaction in self._events if interaction.user_id == user_id
        ]
        return state_items + event_items
