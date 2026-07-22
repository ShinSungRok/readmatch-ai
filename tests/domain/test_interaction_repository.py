import pytest

from readmatch_ai.domain.interaction_repository import InteractionRepository


def test_interaction_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        InteractionRepository()  # type: ignore[abstract]
