from __future__ import annotations

import uuid

from readmatch_ai.domain.interaction import UserInteraction
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.user import UserId


class GetUserInteractionsUseCase:
    """Retrieves every interaction currently recorded for a user.

    An unknown-but-well-formed user id returns an empty list (no
    interactions ever recorded), not an error -- consistent with every
    other user_id-scoped endpoint in this API (e.g.
    GET /recommendations/personalized/{user_id}).
    """

    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._interaction_repository = interaction_repository

    def execute(self, user_id: str) -> list[UserInteraction]:
        return self._interaction_repository.list_by_user(UserId(uuid.UUID(user_id)))
