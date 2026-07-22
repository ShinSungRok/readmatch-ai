import uuid

import pytest

from readmatch_ai.application.record_interaction_use_case import (
    RecordInteractionInput,
    RecordInteractionUseCase,
)
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.interaction import InteractionType
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)


def _setup() -> tuple[RecordInteractionUseCase, InMemoryInteractionRepository, str]:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryInteractionRepository()
    book = RegisterBookUseCase(book_repository).execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    use_case = RecordInteractionUseCase(interaction_repository, book_repository)
    return use_case, interaction_repository, str(book.id.value)


def test_execute_records_a_valid_interaction() -> None:
    use_case, interaction_repository, book_id = _setup()
    user_id = str(uuid.uuid4())

    interaction = use_case.execute(
        RecordInteractionInput(user_id=user_id, book_id=book_id, interaction_type="like")
    )

    assert interaction is not None
    assert interaction.interaction_type == InteractionType.LIKE
    assert len(interaction_repository.list_by_user(interaction.user_id)) == 1


def test_execute_records_a_rating_with_its_value() -> None:
    use_case, _repository, book_id = _setup()

    interaction = use_case.execute(
        RecordInteractionInput(
            user_id=str(uuid.uuid4()), book_id=book_id, interaction_type="rating", value=4
        )
    )

    assert interaction is not None
    assert interaction.value == 4


def test_execute_returns_none_for_an_unknown_but_well_formed_book_id() -> None:
    use_case, _repository, _book_id = _setup()

    result = use_case.execute(
        RecordInteractionInput(
            user_id=str(uuid.uuid4()), book_id=str(uuid.uuid4()), interaction_type="like"
        )
    )

    assert result is None


def test_execute_rejects_a_malformed_user_id() -> None:
    use_case, _repository, book_id = _setup()

    with pytest.raises(ValueError):
        use_case.execute(
            RecordInteractionInput(user_id="not-a-uuid", book_id=book_id, interaction_type="like")
        )


def test_execute_rejects_a_malformed_book_id() -> None:
    use_case, _repository, _book_id = _setup()

    with pytest.raises(ValueError):
        use_case.execute(
            RecordInteractionInput(
                user_id=str(uuid.uuid4()), book_id="not-a-uuid", interaction_type="like"
            )
        )


def test_execute_rejects_an_unknown_interaction_type() -> None:
    use_case, _repository, book_id = _setup()

    with pytest.raises(ValueError):
        use_case.execute(
            RecordInteractionInput(
                user_id=str(uuid.uuid4()), book_id=book_id, interaction_type="not-a-real-type"
            )
        )


def test_execute_rejects_an_invalid_rating_value() -> None:
    use_case, _repository, book_id = _setup()

    with pytest.raises(ValueError):
        use_case.execute(
            RecordInteractionInput(
                user_id=str(uuid.uuid4()), book_id=book_id, interaction_type="rating", value=9
            )
        )


def test_execute_is_idempotent_for_a_state_like_interaction() -> None:
    use_case, interaction_repository, book_id = _setup()
    payload = RecordInteractionInput(
        user_id=str(uuid.uuid4()), book_id=book_id, interaction_type="bookmark"
    )

    first = use_case.execute(payload)
    second = use_case.execute(payload)

    assert first is not None and second is not None
    assert interaction_repository.list_by_user(first.user_id) == [second]
