import pytest

from readmatch_ai.domain.preference_signal_repository import PreferenceSignalRepository


def test_preference_signal_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        PreferenceSignalRepository()  # type: ignore[abstract]
