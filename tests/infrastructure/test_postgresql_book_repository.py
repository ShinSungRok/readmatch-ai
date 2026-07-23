from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_repository import BookNotFoundError, DuplicateISBNError
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "migrations" / "0001_create_books_table.sql"
)


@pytest.fixture(scope="module")
def postgres_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("postgres:16-alpine") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        connection = psycopg.connect(dsn)
        connection.execute(_MIGRATION_PATH.read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def repository(postgres_connection: psycopg.Connection) -> Iterator[PostgreSQLBookRepository]:
    yield PostgreSQLBookRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE books")
    postgres_connection.commit()


def _make_book(isbn: str = "978-3-16-148410-0") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_add_and_get_by_id(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()

    repository.add(book)

    assert repository.get_by_id(book.id) == book


def test_get_by_id_missing_returns_none(repository: PostgreSQLBookRepository) -> None:
    assert repository.get_by_id(BookId.generate()) is None


def test_list_all_returns_every_stored_book(repository: PostgreSQLBookRepository) -> None:
    a = _make_book(isbn="978-3-16-148410-0")
    b = _make_book(isbn="0-306-40615-2")
    repository.add(a)
    repository.add(b)

    assert set(repository.list_all()) == {a, b}


def test_list_all_returns_empty_list_when_no_books_stored(
    repository: PostgreSQLBookRepository,
) -> None:
    assert repository.list_all() == []


def test_get_by_isbn_returns_matching_book(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()
    repository.add(book)

    assert repository.get_by_isbn(book.isbn) == book


def test_get_by_isbn_missing_returns_none(repository: PostgreSQLBookRepository) -> None:
    assert repository.get_by_isbn(ISBN("0-306-40615-2")) is None


def test_update_replaces_existing_book_fields(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()
    repository.add(book)

    revised = Book(
        id=book.id,
        isbn=book.isbn,
        title=Title("Clean Code (2nd Edition)"),
        author=book.author,
        category=book.category,
    )
    repository.update(revised)

    stored = repository.get_by_id(book.id)
    assert stored is not None
    assert stored.title.value == "Clean Code (2nd Edition)"


def test_update_missing_book_raises_not_found(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()

    with pytest.raises(BookNotFoundError):
        repository.update(book)


def test_remove_deletes_book(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()
    repository.add(book)

    repository.remove(book.id)

    assert repository.get_by_id(book.id) is None


def test_remove_missing_book_raises_not_found(repository: PostgreSQLBookRepository) -> None:
    with pytest.raises(BookNotFoundError):
        repository.remove(BookId.generate())


def test_add_duplicate_isbn_raises(repository: PostgreSQLBookRepository) -> None:
    repository.add(_make_book())

    with pytest.raises(DuplicateISBNError):
        repository.add(_make_book())


def test_update_to_another_books_isbn_raises(repository: PostgreSQLBookRepository) -> None:
    first = _make_book(isbn="978-3-16-148410-0")
    second = _make_book(isbn="0-306-40615-2")
    repository.add(first)
    repository.add(second)

    conflicting = Book(
        id=second.id,
        isbn=first.isbn,
        title=second.title,
        author=second.author,
        category=second.category,
    )

    with pytest.raises(DuplicateISBNError):
        repository.update(conflicting)


def test_update_keeping_own_isbn_does_not_raise(repository: PostgreSQLBookRepository) -> None:
    book = _make_book()
    repository.add(book)

    revised = Book(
        id=book.id,
        isbn=book.isbn,
        title=Title("Retitled"),
        author=book.author,
        category=book.category,
    )
    repository.update(revised)

    stored = repository.get_by_id(book.id)
    assert stored is not None
    assert stored.title.value == "Retitled"


def _make_search_book(title: str, author: str, category: str, isbn: str) -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author(author),
        category=Category(category),
    )


def test_search_matches_title_case_insensitively(repository: PostgreSQLBookRepository) -> None:
    book = _make_search_book(
        "The Pragmatic Programmer", "Andrew Hunt", "Software Engineering",
        "978-3-16-148410-0",
    )
    repository.add(book)

    assert repository.search("PRAGMATIC", limit=10) == [book]


def test_search_matches_author(repository: PostgreSQLBookRepository) -> None:
    book = _make_search_book("Dune", "Frank Herbert", "Science Fiction", "0-306-40615-2")
    repository.add(book)

    assert repository.search("herbert", limit=10) == [book]


def test_search_matches_category(repository: PostgreSQLBookRepository) -> None:
    book = _make_search_book("Dune", "Frank Herbert", "Science Fiction", "0-306-40615-2")
    repository.add(book)

    assert repository.search("science", limit=10) == [book]


def test_search_returns_empty_list_when_nothing_matches(
    repository: PostgreSQLBookRepository,
) -> None:
    repository.add(_make_search_book("Dune", "Frank Herbert", "Science Fiction", "0-306-40615-2"))

    assert repository.search("nonexistent", limit=10) == []


def test_search_orders_results_by_title_and_respects_limit(
    repository: PostgreSQLBookRepository,
) -> None:
    zeta = _make_search_book("Zeta Software", "A", "Software Engineering", "978-3-16-148410-0")
    alpha = _make_search_book("Alpha Software", "B", "Software Engineering", "0-306-40615-2")
    repository.add(zeta)
    repository.add(alpha)

    assert repository.search("software", limit=10) == [alpha, zeta]
    assert repository.search("software", limit=1) == [alpha]
