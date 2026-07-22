from __future__ import annotations

import uuid

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import EVENT_LIKE_INTERACTION_TYPES, InteractionType
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.user import UserId


class ClearInteractionUseCase:
    """Removes a previously recorded state-like interaction (e.g. un-bookmark, un-like).

    A no-op if none was recorded -- clearing is safe to call repeatedly.
    Rejects CLICK (event-like: there is no single state to clear).
    """

    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._interaction_repository = interaction_repository

    def execute(self, user_id: str, book_id: str, interaction_type: str) -> None:
        parsed_type = InteractionType(interaction_type)
        if parsed_type in EVENT_LIKE_INTERACTION_TYPES:
            raise ValueError(f"{parsed_type.value} is event-like and cannot be cleared")
        self._interaction_repository.clear(
            UserId(uuid.UUID(user_id)), BookId(uuid.UUID(book_id)), parsed_type
        )
