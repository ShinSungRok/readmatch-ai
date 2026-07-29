from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_preference_signal_repository import (
    InMemoryPreferenceSignalRepository,
)


def test_record_and_retrieve_a_signal_by_user() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()
    signal = UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "healing novel")

    repository.record(signal)

    assert repository.list_by_user(user_id) == [signal]


def test_signals_accumulate_instead_of_overwriting() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()
    first = UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "first query")
    second = UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "second query")

    repository.record(first)
    repository.record(second)

    assert repository.list_by_user(user_id) == [first, second]


def test_list_by_user_only_returns_that_users_signals() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id, other_user_id = UserId.generate(), UserId.generate()
    repository.record(UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "query"))
    repository.record(UserPreferenceSignal(other_user_id, PreferenceSignalType.SEARCH, "query"))

    assert len(repository.list_by_user(user_id)) == 1


def test_list_by_user_returns_empty_for_a_user_with_no_signals() -> None:
    repository = InMemoryPreferenceSignalRepository()

    assert repository.list_by_user(UserId.generate()) == []


def test_clear_removes_every_signal_of_the_given_type() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()
    repository.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction")
    )
    repository.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "History")
    )

    repository.clear(user_id, PreferenceSignalType.CATEGORY_INTEREST)

    assert repository.list_by_user(user_id) == []


def test_clear_is_a_no_op_when_nothing_was_recorded() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()

    repository.clear(user_id, PreferenceSignalType.CATEGORY_INTEREST)

    assert repository.list_by_user(user_id) == []


def test_clear_only_removes_the_targeted_type_and_user() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id, other_user_id = UserId.generate(), UserId.generate()
    kept_search = UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "query")
    kept_other_user = UserPreferenceSignal(
        other_user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction"
    )
    repository.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction")
    )
    repository.record(kept_search)
    repository.record(kept_other_user)

    repository.clear(user_id, PreferenceSignalType.CATEGORY_INTEREST)

    assert repository.list_by_user(user_id) == [kept_search]
    assert repository.list_by_user(other_user_id) == [kept_other_user]
