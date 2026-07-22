import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_repository import BookNotFoundError, DuplicateISBNError
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def _make_book(isbn: str = "978-3-16-148410-0") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_add_and_get_by_id() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()

    repo.add(book)

    assert repo.get_by_id(book.id) == book


def test_get_by_id_missing_returns_none() -> None:
    repo = InMemoryBookRepository()

    assert repo.get_by_id(BookId.generate()) is None


def test_list_all_returns_every_stored_book() -> None:
    repo = InMemoryBookRepository()
    a = _make_book(isbn="978-3-16-148410-0")
    b = _make_book(isbn="0-306-40615-2")
    repo.add(a)
    repo.add(b)

    assert set(repo.list_all()) == {a, b}


def test_list_all_returns_empty_list_when_no_books_stored() -> None:
    repo = InMemoryBookRepository()

    assert repo.list_all() == []


def test_get_by_isbn_returns_matching_book() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()
    repo.add(book)

    assert repo.get_by_isbn(book.isbn) == book


def test_get_by_isbn_missing_returns_none() -> None:
    repo = InMemoryBookRepository()

    assert repo.get_by_isbn(ISBN("0-306-40615-2")) is None


def test_update_replaces_existing_book_fields() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()
    repo.add(book)

    revised = Book(
        id=book.id,
        isbn=book.isbn,
        title=Title("Clean Code (2nd Edition)"),
        author=book.author,
        category=book.category,
    )
    repo.update(revised)

    stored = repo.get_by_id(book.id)
    assert stored is not None
    assert stored.title.value == "Clean Code (2nd Edition)"


def test_update_missing_book_raises_not_found() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()

    with pytest.raises(BookNotFoundError):
        repo.update(book)


def test_remove_deletes_book() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()
    repo.add(book)

    repo.remove(book.id)

    assert repo.get_by_id(book.id) is None


def test_remove_missing_book_raises_not_found() -> None:
    repo = InMemoryBookRepository()

    with pytest.raises(BookNotFoundError):
        repo.remove(BookId.generate())


def test_add_duplicate_isbn_raises() -> None:
    repo = InMemoryBookRepository()
    repo.add(_make_book())

    with pytest.raises(DuplicateISBNError):
        repo.add(_make_book())


def test_update_to_another_books_isbn_raises() -> None:
    repo = InMemoryBookRepository()
    first = _make_book(isbn="978-3-16-148410-0")
    second = _make_book(isbn="0-306-40615-2")
    repo.add(first)
    repo.add(second)

    conflicting = Book(
        id=second.id,
        isbn=first.isbn,
        title=second.title,
        author=second.author,
        category=second.category,
    )

    with pytest.raises(DuplicateISBNError):
        repo.update(conflicting)


def test_update_keeping_own_isbn_does_not_raise() -> None:
    repo = InMemoryBookRepository()
    book = _make_book()
    repo.add(book)

    revised = Book(
        id=book.id,
        isbn=book.isbn,
        title=Title("Retitled"),
        author=book.author,
        category=book.category,
    )
    repo.update(revised)

    stored = repo.get_by_id(book.id)
    assert stored is not None
    assert stored.title.value == "Retitled"
