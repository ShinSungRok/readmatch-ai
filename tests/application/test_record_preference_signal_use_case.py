import uuid

import pytest

from readmatch_ai.application.record_preference_signal_use_case import (
    RecordPreferenceSignalInput,
    RecordPreferenceSignalUseCase,
)
from readmatch_ai.domain.preference_signal import PreferenceSignalType
from readmatch_ai.infrastructure.in_memory_preference_signal_repository import (
    InMemoryPreferenceSignalRepository,
)


def test_execute_records_a_category_interest_signal() -> None:
    repository = InMemoryPreferenceSignalRepository()
    use_case = RecordPreferenceSignalUseCase(repository)
    user_id = str(uuid.uuid4())

    signal = use_case.execute(
        RecordPreferenceSignalInput(user_id, "category_interest", "Fiction")
    )

    assert signal.signal_type == PreferenceSignalType.CATEGORY_INTEREST
    assert signal.value == "Fiction"


def test_execute_trims_the_value() -> None:
    repository = InMemoryPreferenceSignalRepository()
    use_case = RecordPreferenceSignalUseCase(repository)

    signal = use_case.execute(
        RecordPreferenceSignalInput(str(uuid.uuid4()), "search", "  healing novel  ")
    )

    assert signal.value == "healing novel"


def test_execute_rejects_a_malformed_user_id() -> None:
    use_case = RecordPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    with pytest.raises(ValueError):
        use_case.execute(RecordPreferenceSignalInput("not-a-uuid", "search", "query"))


def test_execute_rejects_an_unknown_signal_type() -> None:
    use_case = RecordPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    with pytest.raises(ValueError):
        use_case.execute(
            RecordPreferenceSignalInput(str(uuid.uuid4()), "not-a-real-type", "query")
        )


def test_execute_rejects_a_blank_value() -> None:
    use_case = RecordPreferenceSignalUseCase(InMemoryPreferenceSignalRepository())

    with pytest.raises(ValueError):
        use_case.execute(RecordPreferenceSignalInput(str(uuid.uuid4()), "search", "   "))
