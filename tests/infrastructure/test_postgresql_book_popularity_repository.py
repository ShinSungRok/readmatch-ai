from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.infrastructure.in_memory_import_history_repository import (
    InMemoryImportHistoryRepository,
)
from readmatch_ai.infrastructure.postgresql_book_popularity_repository import (
    PostgreSQLBookPopularityRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class FakeBookDataSource(BookDataSource):
    """Mocked BookDataSource — the real Data4Library API is never called in this test."""

    def __init__(self, books: list[PopularLoanBook]) -> None:
        self._books = books

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        return self._books


@pytest.fixture(scope="module")
def postgres_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("postgres:16-alpine") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        connection = psycopg.connect(dsn)
        connection.execute((_MIGRATIONS_DIR / "0001_create_books_table.sql").read_text())
        connection.execute((_MIGRATIONS_DIR / "0002_create_book_popularity_table.sql").read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def book_repository(postgres_connection: psycopg.Connection) -> PostgreSQLBookRepository:
    return PostgreSQLBookRepository(postgres_connection)


@pytest.fixture
def popularity_repository(
    postgres_connection: psycopg.Connection,
) -> Iterator[PostgreSQLBookPopularityRepository]:
    yield PostgreSQLBookPopularityRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE book_popularity")
    postgres_connection.execute("TRUNCATE TABLE books CASCADE")
    postgres_connection.commit()


def _add_book(book_repository: PostgreSQLBookRepository, isbn: str) -> Book:
    book = Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )
    book_repository.add(book)
    return book


def test_record_and_top_by_loan_count(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")

    popularity_repository.record(BookPopularity(book.id, 100, "2024-01-01", "2024-01-31"))

    top = popularity_repository.top_by_loan_count(10)
    assert top == [BookPopularity(book.id, 100, "2024-01-01", "2024-01-31")]


def test_get_by_book_id_returns_the_recorded_popularity(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    popularity_repository.record(BookPopularity(book.id, 42, "2024-01-01", "2024-01-31"))

    assert popularity_repository.get_by_book_id(book.id) == BookPopularity(
        book.id, 42, "2024-01-01", "2024-01-31"
    )


def test_get_by_book_id_returns_none_when_never_recorded(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")

    assert popularity_repository.get_by_book_id(book.id) is None


def test_ranking_orders_by_loan_count_descending(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    low = _add_book(book_repository, "978-3-16-148410-0")
    high = _add_book(book_repository, "0-306-40615-2")
    popularity_repository.record(BookPopularity(low.id, 10, "2024-01-01", "2024-01-31"))
    popularity_repository.record(BookPopularity(high.id, 999, "2024-01-01", "2024-01-31"))

    top = popularity_repository.top_by_loan_count(10)

    assert [p.book_id for p in top] == [high.id, low.id]


def test_limit_truncates_results(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    isbns = ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]
    for isbn in isbns:
        book = _add_book(book_repository, isbn)
        popularity_repository.record(BookPopularity(book.id, 10, "2024-01-01", "2024-01-31"))

    assert len(popularity_repository.top_by_loan_count(2)) == 2


def test_repeated_period_upserts_same_book(
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    popularity_repository.record(BookPopularity(book.id, 100, "2024-01-01", "2024-01-31"))

    popularity_repository.record(BookPopularity(book.id, 500, "2024-02-01", "2024-02-29"))

    top = popularity_repository.top_by_loan_count(10)
    assert top == [BookPopularity(book.id, 500, "2024-02-01", "2024-02-29")]


def test_repeated_book_import_refreshes_popularity_via_postgresql(
    postgres_connection: psycopg.Connection,
    book_repository: PostgreSQLBookRepository,
    popularity_repository: PostgreSQLBookPopularityRepository,
) -> None:
    source_book = PopularLoanBook(
        isbn13="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=100,
    )
    first_use_case = ImportBooksUseCase(
        FakeBookDataSource([source_book]),
        book_repository,
        popularity_repository,
        InMemoryImportHistoryRepository(),
    )
    first_result = first_use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))
    existing_book_id = first_result.imported[0].id

    reimported_book = PopularLoanBook(
        isbn13="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=777,
    )
    second_use_case = ImportBooksUseCase(
        FakeBookDataSource([reimported_book]),
        book_repository,
        popularity_repository,
        InMemoryImportHistoryRepository(),
    )
    second_result = second_use_case.execute(PopularLoanBooksQuery("2024-02-01", "2024-02-29"))

    assert second_result.imported == []
    assert len(second_result.updated) == 1
    assert second_result.updated[0].id == existing_book_id

    top = popularity_repository.top_by_loan_count(10)
    assert len(top) == 1
    assert top[0].book_id == existing_book_id
    assert top[0].loan_count == 777
    assert top[0].period_start == "2024-02-01"

    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM books WHERE isbn = %s", ("9783161484100",))
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == 1
