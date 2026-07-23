import pytest

from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.user import UserId


def test_constructs_with_a_non_empty_value() -> None:
    signal = UserPreferenceSignal(UserId.generate(), PreferenceSignalType.SEARCH, "healing novel")

    assert signal.value == "healing novel"


@pytest.mark.parametrize("blank_value", ["", "   "])
def test_rejects_a_blank_value(blank_value: str) -> None:
    with pytest.raises(ValueError, match="non-empty value"):
        UserPreferenceSignal(UserId.generate(), PreferenceSignalType.SEARCH, blank_value)


def test_unknown_signal_type_string_is_rejected() -> None:
    with pytest.raises(ValueError):
        PreferenceSignalType("not-a-real-type")
