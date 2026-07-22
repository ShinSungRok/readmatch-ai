import uuid

import pytest

from readmatch_ai.application.clear_interaction_use_case import ClearInteractionUseCase
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)


def test_execute_clears_a_recorded_interaction() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    repository.record(UserInteraction(user_id, book_id, InteractionType.LIKE))
    use_case = ClearInteractionUseCase(repository)

    use_case.execute(str(user_id.value), str(book_id.value), "like")

    assert repository.list_by_user(user_id) == []


def test_execute_is_a_no_op_when_nothing_was_recorded() -> None:
    repository = InMemoryInteractionRepository()
    use_case = ClearInteractionUseCase(repository)

    use_case.execute(str(uuid.uuid4()), str(uuid.uuid4()), "bookmark")


def test_execute_rejects_clearing_click() -> None:
    use_case = ClearInteractionUseCase(InMemoryInteractionRepository())

    with pytest.raises(ValueError, match="event-like"):
        use_case.execute(str(uuid.uuid4()), str(uuid.uuid4()), "click")


def test_execute_rejects_an_unknown_interaction_type() -> None:
    use_case = ClearInteractionUseCase(InMemoryInteractionRepository())

    with pytest.raises(ValueError):
        use_case.execute(str(uuid.uuid4()), str(uuid.uuid4()), "not-a-real-type")


def test_execute_rejects_a_malformed_user_id() -> None:
    use_case = ClearInteractionUseCase(InMemoryInteractionRepository())

    with pytest.raises(ValueError):
        use_case.execute("not-a-uuid", str(uuid.uuid4()), "like")
