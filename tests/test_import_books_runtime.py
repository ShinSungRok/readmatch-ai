import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_PATH = _REPO_ROOT / "migrations" / "0001_create_books_table.sql"


def _load_import_books_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "import_books_script", _REPO_ROOT / "scripts" / "import_books.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = _load_import_books_module().main


class FakeBookDataSource(BookDataSource):
    """Mocked BookDataSource — the real Data4Library API is never called in this test."""

    def __init__(self, books: list[PopularLoanBook]) -> None:
        self._books = books

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        return self._books


@pytest.fixture
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


def test_import_runner_persists_and_is_retrievable_via_postgresql(
    postgres_connection: psycopg.Connection,
) -> None:
    context = ApplicationContext.create(
        book_repository=PostgreSQLBookRepository(postgres_connection)
    )
    fake_source = FakeBookDataSource(
        [
            PopularLoanBook(
                isbn13="978-3-16-148410-0",
                title="Clean Code",
                author="Robert C. Martin",
                publisher="Prentice Hall",
                category="Software Engineering",
                loan_count=100,
            )
        ]
    )

    exit_code = main(
        ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        book_data_source=fake_source,
        application_context=context,
    )

    assert exit_code == 0

    retrieved_by_isbn = context.get_book_by_isbn_use_case.execute("978-3-16-148410-0")
    assert retrieved_by_isbn is not None
    assert retrieved_by_isbn.title.value == "Clean Code"

    retrieved_by_id = context.get_book_by_id_use_case.execute(str(retrieved_by_isbn.id.value))
    assert retrieved_by_id == retrieved_by_isbn

    # Verifies persistence through a fresh PostgreSQLBookRepository against the
    # same database, not just an in-process object reference.
    fresh_repository = PostgreSQLBookRepository(postgres_connection)
    assert fresh_repository.get_by_isbn(retrieved_by_isbn.isbn) == retrieved_by_isbn


def test_import_runner_reports_skipped_duplicates(postgres_connection: psycopg.Connection) -> None:
    context = ApplicationContext.create(
        book_repository=PostgreSQLBookRepository(postgres_connection)
    )
    duplicate_book = PopularLoanBook(
        isbn13="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=100,
    )
    fake_source = FakeBookDataSource([duplicate_book, duplicate_book])

    exit_code = main(
        ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        book_data_source=fake_source,
        application_context=context,
    )

    assert exit_code == 0
    assert context.get_book_by_isbn_use_case.execute("978-3-16-148410-0") is not None
