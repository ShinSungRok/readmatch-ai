from __future__ import annotations

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository


class InMemoryUserBookInteractionRepository(UserBookInteractionRepository):
    """In-process UserBookInteractionRepository adapter backed by a dict."""

    def __init__(self) -> None:
        self._interactions: dict[tuple[UserId, BookId], UserBookInteraction] = {}

    def record(self, interaction: UserBookInteraction) -> None:
        self._interactions[(interaction.user_id, interaction.book_id)] = interaction

    def list_all(self) -> list[UserBookInteraction]:
        return list(self._interactions.values())

    def list_by_user(self, user_id: UserId) -> list[UserBookInteraction]:
        return [
            interaction
            for interaction in self._interactions.values()
            if interaction.user_id == user_id
        ]
