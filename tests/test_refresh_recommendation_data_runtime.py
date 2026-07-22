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
from readmatch_ai.infrastructure.postgresql_book_embedding_repository import (
    PostgreSQLBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository
from readmatch_ai.infrastructure.postgresql_sync_checkpoint_repository import (
    PostgreSQLSyncCheckpointRepository,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_MIGRATIONS = (
    "0001_create_books_table.sql",
    "0002_create_book_popularity_table.sql",
    "0003_create_book_embeddings_table.sql",
    "0004_add_pgvector_to_book_embeddings.sql",
    "0005_widen_book_embeddings_vector_to_384.sql",
    "0007_add_model_version_and_content_hash_to_book_embeddings.sql",
    "0008_configure_hnsw_index_parameters.sql",
    "0009_create_sync_checkpoint_table.sql",
)


def _load_module(name: str, relative_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = _load_module(
    "refresh_recommendation_data_script", "scripts/refresh_recommendation_data.py"
).main


class FakeBookDataSource(BookDataSource):
    """Mocked BookDataSource — the real Data4Library API is never called in this test."""

    def __init__(self, books: list[PopularLoanBook]) -> None:
        self._books = books

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        return self._books


def _popular_loan_book(isbn13: str = "978-3-16-148410-0") -> PopularLoanBook:
    return PopularLoanBook(
        isbn13=isbn13,
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=100,
    )


@pytest.fixture
def postgres_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("pgvector/pgvector:pg16") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        connection = psycopg.connect(dsn)
        for migration in _MIGRATIONS:
            connection.execute((_MIGRATIONS_DIR / migration).read_text())
        connection.commit()
        yield connection
        connection.close()


def _context(postgres_connection: psycopg.Connection) -> ApplicationContext:
    return ApplicationContext.create(
        book_repository=PostgreSQLBookRepository(postgres_connection),
        book_embedding_repository=PostgreSQLBookEmbeddingRepository(postgres_connection),
        sync_checkpoint_repository=PostgreSQLSyncCheckpointRepository(postgres_connection),
    )


def test_refresh_pipeline_persists_book_embedding_and_checkpoint_via_postgresql(
    postgres_connection: psycopg.Connection,
) -> None:
    context = _context(postgres_connection)
    fake_source = FakeBookDataSource([_popular_loan_book()])

    exit_code = main(
        ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        book_data_source=fake_source,
        application_context=context,
    )

    assert exit_code == 0
    book = context.get_book_by_isbn_use_case.execute("978-3-16-148410-0")
    assert book is not None
    assert context.book_embedding_repository.get_by_book_id(book.id) is not None
    assert context.book_popularity_repository.get_by_book_id(book.id) is not None
    checkpoint = context.sync_checkpoint_repository.get()
    assert checkpoint is not None
    assert checkpoint.period_end == "2024-01-31"

    # Verifies persistence through fresh adapters against the same database,
    # not just in-process object references.
    fresh_book_repository = PostgreSQLBookRepository(postgres_connection)
    assert fresh_book_repository.get_by_isbn(book.isbn) == book


def test_repeated_refresh_of_identical_data_is_idempotent_via_postgresql(
    postgres_connection: psycopg.Connection,
) -> None:
    context = _context(postgres_connection)

    first_exit_code = main(
        ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        book_data_source=FakeBookDataSource([_popular_loan_book()]),
        application_context=context,
    )
    second_exit_code = main(
        ["--start-date", "2024-02-01", "--end-date", "2024-02-29"],
        book_data_source=FakeBookDataSource([_popular_loan_book()]),
        application_context=context,
    )

    assert first_exit_code == 0
    assert second_exit_code == 0
    books = PostgreSQLBookRepository(postgres_connection).list_all()
    assert len(books) == 1

    checkpoint = context.sync_checkpoint_repository.get()
    assert checkpoint is not None
    assert checkpoint.period_end == "2024-02-29"


def test_refresh_pipeline_does_not_advance_checkpoint_when_sync_fails(
    postgres_connection: psycopg.Connection,
) -> None:
    class FailingBookDataSource(BookDataSource):
        def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
            raise ConnectionError("simulated Data4Library outage")

    context = _context(postgres_connection)

    with pytest.raises(ConnectionError):
        main(
            ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
            book_data_source=FailingBookDataSource(),
            application_context=context,
        )

    assert context.sync_checkpoint_repository.get() is None
