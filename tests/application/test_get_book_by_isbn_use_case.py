from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def test_get_book_by_isbn_returns_matching_book() -> None:
    repo = InMemoryBookRepository()
    registered = RegisterBookUseCase(repo).execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    use_case = GetBookByISBNUseCase(repo)

    assert use_case.execute("978-3-16-148410-0") == registered


def test_get_book_by_isbn_returns_none_when_missing() -> None:
    repo = InMemoryBookRepository()
    use_case = GetBookByISBNUseCase(repo)

    assert use_case.execute("0-306-40615-2") is None
