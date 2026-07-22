from __future__ import annotations

import uuid
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class RecordInteractionInput:
    user_id: str
    book_id: str
    interaction_type: str
    value: int | None = None


class RecordInteractionUseCase:
    """Records an explicit user interaction against a book.

    Malformed input (invalid user/book id, unknown interaction type, or an
    invalid rating value) raises ValueError -- translated to HTTP 400 by
    the existing global handler (see api.errors), consistent with every
    other id-parsing use case in this codebase. A well-formed but unknown
    book id returns None instead of raising, mirroring
    GetBookDetailUseCase's "safe not-found" convention -- the router turns
    that into a 404.
    """

    def __init__(
        self, interaction_repository: InteractionRepository, book_repository: BookRepository
    ) -> None:
        self._interaction_repository = interaction_repository
        self._book_repository = book_repository

    def execute(self, input_data: RecordInteractionInput) -> UserInteraction | None:
        user_id = UserId(uuid.UUID(input_data.user_id))
        book_id = BookId(uuid.UUID(input_data.book_id))
        if self._book_repository.get_by_id(book_id) is None:
            return None
        interaction_type = InteractionType(input_data.interaction_type)
        interaction = UserInteraction(
            user_id=user_id,
            book_id=book_id,
            interaction_type=interaction_type,
            value=input_data.value,
        )
        self._interaction_repository.record(interaction)
        return interaction
