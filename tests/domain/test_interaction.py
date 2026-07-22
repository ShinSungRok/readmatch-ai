import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId


def _ids() -> tuple[UserId, BookId]:
    return UserId.generate(), BookId.generate()


@pytest.mark.parametrize(
    "interaction_type",
    [
        InteractionType.CLICK,
        InteractionType.LIKE,
        InteractionType.DISLIKE,
        InteractionType.BOOKMARK,
        InteractionType.READ,
    ],
)
def test_non_rating_interaction_constructs_without_a_value(
    interaction_type: InteractionType,
) -> None:
    user_id, book_id = _ids()

    interaction = UserInteraction(user_id, book_id, interaction_type)

    assert interaction.value is None


@pytest.mark.parametrize(
    "interaction_type",
    [
        InteractionType.CLICK,
        InteractionType.LIKE,
        InteractionType.DISLIKE,
        InteractionType.BOOKMARK,
        InteractionType.READ,
    ],
)
def test_non_rating_interaction_with_a_value_is_rejected(
    interaction_type: InteractionType,
) -> None:
    user_id, book_id = _ids()

    with pytest.raises(ValueError, match="must not include a value"):
        UserInteraction(user_id, book_id, interaction_type, value=3)


def test_rating_interaction_requires_a_value() -> None:
    user_id, book_id = _ids()

    with pytest.raises(ValueError, match="requires a value"):
        UserInteraction(user_id, book_id, InteractionType.RATING)


@pytest.mark.parametrize("value", [0, 6, -1])
def test_rating_interaction_rejects_an_out_of_range_value(value: int) -> None:
    user_id, book_id = _ids()

    with pytest.raises(ValueError, match="between 1 and 5"):
        UserInteraction(user_id, book_id, InteractionType.RATING, value=value)


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
def test_rating_interaction_accepts_every_in_range_value(value: int) -> None:
    user_id, book_id = _ids()

    interaction = UserInteraction(user_id, book_id, InteractionType.RATING, value=value)

    assert interaction.value == value


def test_unknown_interaction_type_string_is_rejected() -> None:
    with pytest.raises(ValueError):
        InteractionType("not-a-real-type")
