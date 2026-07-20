from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)


def _interaction(user_id: UserId, book_id: BookId, count: int = 1) -> UserBookInteraction:
    return UserBookInteraction(user_id=user_id, book_id=book_id, interaction_count=count)


def test_list_all_is_empty_initially() -> None:
    repository = InMemoryUserBookInteractionRepository()

    assert repository.list_all() == []


def test_record_and_list_all() -> None:
    repository = InMemoryUserBookInteractionRepository()
    interaction = _interaction(UserId.generate(), BookId.generate())

    repository.record(interaction)

    assert repository.list_all() == [interaction]


def test_record_upserts_by_user_and_book() -> None:
    repository = InMemoryUserBookInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    repository.record(_interaction(user_id, book_id, count=1))

    repository.record(_interaction(user_id, book_id, count=5))

    assert repository.list_all() == [_interaction(user_id, book_id, count=5)]


def test_list_by_user_returns_only_that_users_interactions() -> None:
    repository = InMemoryUserBookInteractionRepository()
    user_a, user_b = UserId.generate(), UserId.generate()
    interaction_a = _interaction(user_a, BookId.generate())
    interaction_b = _interaction(user_b, BookId.generate())
    repository.record(interaction_a)
    repository.record(interaction_b)

    assert repository.list_by_user(user_a) == [interaction_a]


def test_list_by_user_returns_empty_for_unknown_user() -> None:
    repository = InMemoryUserBookInteractionRepository()

    assert repository.list_by_user(UserId.generate()) == []
