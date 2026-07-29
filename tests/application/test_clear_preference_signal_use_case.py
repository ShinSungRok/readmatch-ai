import uuid

import pytest

from readmatch_ai.application.clear_preference_signal_use_case import ClearPreferenceSignalUseCase
from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_preference_signal_repository import (
    InMemoryPreferenceSignalRepository,
)


def test_execute_clears_every_signal_of_the_given_type() -> None:
    repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()
    repository.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction")
    )
    use_case = ClearPreferenceSignalUseCase(repository)

    use_case.execute(str(user_id.value), "category_interest")

    assert repository.list_by_user(user_id) == []


def test_execute_is_a_no_op_when_nothing_was_recorded() -> None:
    use_case = ClearPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    use_case.execute(str(uuid.uuid4()), "category_interest")


def test_execute_rejects_an_unknown_signal_type() -> None:
    use_case = ClearPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    with pytest.raises(ValueError):
        use_case.execute(str(uuid.uuid4()), "not-a-real-type")


def test_execute_rejects_a_malformed_user_id() -> None:
    use_case = ClearPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    with pytest.raises(ValueError):
        use_case.execute("not-a-uuid", "category_interest")
