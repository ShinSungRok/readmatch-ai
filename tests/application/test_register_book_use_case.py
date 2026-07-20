import pytest

from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book_repository import DuplicateISBNError
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def _valid_input(isbn: str = "978-3-16-148410-0") -> RegisterBookInput:
    return RegisterBookInput(
        isbn=isbn,
        title="Clean Code",
        author="Robert C. Martin",
        category="Software Engineering",
    )


def test_register_book_persists_via_repository() -> None:
    repo = InMemoryBookRepository()
    use_case = RegisterBookUseCase(repo)

    book = use_case.execute(_valid_input())

    assert repo.get_by_id(book.id) == book
    assert book.isbn.value == "9783161484100"
    assert book.title.value == "Clean Code"


def test_register_book_rejects_duplicate_isbn() -> None:
    repo = InMemoryBookRepository()
    use_case = RegisterBookUseCase(repo)
    use_case.execute(_valid_input())

    with pytest.raises(DuplicateISBNError):
        use_case.execute(_valid_input())


def test_register_book_rejects_invalid_isbn() -> None:
    repo = InMemoryBookRepository()
    use_case = RegisterBookUseCase(repo)

    with pytest.raises(ValueError):
        use_case.execute(_valid_input(isbn="not-an-isbn"))
