import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_repository import BookRepository


class InMemoryBookRepository(BookRepository):
    """Test-only fake used to verify the port's contract; not a production adapter."""

    def __init__(self) -> None:
        self._books: dict[BookId, Book] = {}

    def add(self, book: Book) -> None:
        self._books[book.id] = book

    def get_by_id(self, book_id: BookId) -> Book | None:
        return self._books.get(book_id)

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        return next((b for b in self._books.values() if b.isbn == isbn), None)


def _make_book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_book_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookRepository()  # type: ignore[abstract]


def test_in_memory_repository_add_and_get_by_id() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()

    repo.add(book)

    assert repo.get_by_id(book.id) == book


def test_in_memory_repository_get_by_id_missing_returns_none() -> None:
    repo = InMemoryBookRepository()

    assert repo.get_by_id(BookId.generate()) is None


def test_in_memory_repository_get_by_isbn() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()
    repo.add(book)

    assert repo.get_by_isbn(book.isbn) == book
    assert repo.get_by_isbn(ISBN("0-306-40615-2")) is None
