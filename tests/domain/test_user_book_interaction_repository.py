import pytest

from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository


def test_user_book_interaction_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        UserBookInteractionRepository()  # type: ignore[abstract]
