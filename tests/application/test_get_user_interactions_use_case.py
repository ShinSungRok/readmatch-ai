import uuid

from readmatch_ai.application.get_user_interactions_use_case import GetUserInteractionsUseCase
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)


def test_execute_returns_the_users_recorded_interactions() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    interaction = UserInteraction(user_id, book_id, InteractionType.LIKE)
    repository.record(interaction)
    use_case = GetUserInteractionsUseCase(repository)

    result = use_case.execute(str(user_id.value))

    assert result == [interaction]


def test_execute_returns_an_empty_list_for_an_unknown_user() -> None:
    use_case = GetUserInteractionsUseCase(InMemoryInteractionRepository())

    assert use_case.execute(str(uuid.uuid4())) == []
