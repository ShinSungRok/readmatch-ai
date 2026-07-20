import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction


def test_constructs_with_a_positive_interaction_count() -> None:
    user_id = UserId.generate()
    book_id = BookId.generate()

    interaction = UserBookInteraction(user_id=user_id, book_id=book_id, interaction_count=3)

    assert interaction.user_id == user_id
    assert interaction.book_id == book_id
    assert interaction.interaction_count == 3


@pytest.mark.parametrize("invalid_count", [0, -1])
def test_rejects_a_non_positive_interaction_count(invalid_count: int) -> None:
    with pytest.raises(ValueError, match="interaction_count"):
        UserBookInteraction(
            user_id=UserId.generate(), book_id=BookId.generate(), interaction_count=invalid_count
        )
