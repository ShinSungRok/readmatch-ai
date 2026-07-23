from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)


def test_record_a_state_like_interaction_and_retrieve_it_by_user() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    interaction = UserInteraction(user_id, book_id, InteractionType.LIKE)

    repository.record(interaction)

    assert repository.list_by_user(user_id) == [interaction]


def test_recording_a_state_like_interaction_again_replaces_the_prior_value() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    repository.record(UserInteraction(user_id, book_id, InteractionType.RATING, value=3))

    repository.record(UserInteraction(user_id, book_id, InteractionType.RATING, value=5))

    interactions = repository.list_by_user(user_id)
    assert len(interactions) == 1
    assert interactions[0].value == 5


def test_recording_the_same_state_like_interaction_twice_is_idempotent() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    interaction = UserInteraction(user_id, book_id, InteractionType.BOOKMARK)

    repository.record(interaction)
    repository.record(interaction)

    assert repository.list_by_user(user_id) == [interaction]


def test_click_events_accumulate_instead_of_overwriting() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    interaction = UserInteraction(user_id, book_id, InteractionType.CLICK)

    repository.record(interaction)
    repository.record(interaction)
    repository.record(interaction)

    assert repository.list_by_user(user_id) == [interaction, interaction, interaction]


def test_view_events_accumulate_instead_of_overwriting() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    interaction = UserInteraction(user_id, book_id, InteractionType.VIEW)

    repository.record(interaction)
    repository.record(interaction)

    assert repository.list_by_user(user_id) == [interaction, interaction]


def test_clear_removes_a_recorded_state_like_interaction() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    repository.record(UserInteraction(user_id, book_id, InteractionType.LIKE))

    repository.clear(user_id, book_id, InteractionType.LIKE)

    assert repository.list_by_user(user_id) == []


def test_clear_is_a_no_op_when_nothing_was_recorded() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()

    repository.clear(user_id, book_id, InteractionType.LIKE)

    assert repository.list_by_user(user_id) == []


def test_clear_only_removes_the_targeted_interaction_type() -> None:
    repository = InMemoryInteractionRepository()
    user_id, book_id = UserId.generate(), BookId.generate()
    repository.record(UserInteraction(user_id, book_id, InteractionType.LIKE))
    repository.record(UserInteraction(user_id, book_id, InteractionType.BOOKMARK))

    repository.clear(user_id, book_id, InteractionType.LIKE)

    remaining_types = {i.interaction_type for i in repository.list_by_user(user_id)}
    assert remaining_types == {InteractionType.BOOKMARK}


def test_list_by_user_only_returns_that_users_interactions() -> None:
    repository = InMemoryInteractionRepository()
    user_id, other_user_id = UserId.generate(), UserId.generate()
    book_id = BookId.generate()
    repository.record(UserInteraction(user_id, book_id, InteractionType.LIKE))
    repository.record(UserInteraction(other_user_id, book_id, InteractionType.LIKE))

    assert len(repository.list_by_user(user_id)) == 1


def test_list_by_user_returns_empty_for_a_user_with_no_interactions() -> None:
    repository = InMemoryInteractionRepository()

    assert repository.list_by_user(UserId.generate()) == []
