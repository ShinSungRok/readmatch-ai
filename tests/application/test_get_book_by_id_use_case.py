import uuid

from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def test_get_book_by_id_returns_matching_book() -> None:
    repo = InMemoryBookRepository()
    registered = RegisterBookUseCase(repo).execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    use_case = GetBookByIdUseCase(repo)

    assert use_case.execute(str(registered.id.value)) == registered


def test_get_book_by_id_returns_none_when_missing() -> None:
    repo = InMemoryBookRepository()
    use_case = GetBookByIdUseCase(repo)

    assert use_case.execute(str(uuid.uuid4())) is None
