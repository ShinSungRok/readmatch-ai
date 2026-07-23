import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.postgresql_book_metadata_repository import (
    PostgreSQLBookMetadataRepository,
)
from readmatch_ai.infrastructure.postgresql_book_popularity_repository import (
    PostgreSQLBookPopularityRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_PATHS = (
    _REPO_ROOT / "migrations" / "0001_create_books_table.sql",
    _REPO_ROOT / "migrations" / "0002_create_book_popularity_table.sql",
    _REPO_ROOT / "migrations" / "0010_create_book_metadata_table.sql",
)


def _load_seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "seed_demo_data_script", _REPO_ROOT / "scripts" / "seed_demo_data.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_seed_module = _load_seed_module()
main = _seed_module.main
SampleFileBookDataSource = _seed_module.SampleFileBookDataSource

_SAMPLE_RECORDS = [
    {
        "source": "data4library",
        "title": "Clean Code",
        "authors": "지은이: Robert C. Martin",
        "publisher": "Prentice Hall",
        "publication_year": 2008,
        "isbn13": "9780132350884",
        "category": "Software Engineering",
        "cover_url": "https://example.test/covers/clean-code.jpg",
        "detail_url": "https://example.test/detail/1",
        "loan_count": 120,
    },
    {
        "source": "data4library",
        "title": "Dune",
        "authors": "지은이: Frank Herbert",
        "publisher": "Chilton Books",
        "publication_year": 1965,
        "isbn13": "9780441013593",
        "category": "Science Fiction",
        "cover_url": "https://example.test/covers/dune.jpg",
        "detail_url": "https://example.test/detail/2",
        "loan_count": 150,
    },
]


@pytest.fixture
def sample_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(_SAMPLE_RECORDS), encoding="utf-8")
    return path


@pytest.fixture
def postgres_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("postgres:16-alpine") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        connection = psycopg.connect(dsn)
        for migration_path in _MIGRATION_PATHS:
            connection.execute(migration_path.read_text())
        connection.commit()
        yield connection
        connection.close()


def _build_context(connection: psycopg.Connection) -> ApplicationContext:
    return ApplicationContext.create(
        book_repository=PostgreSQLBookRepository(connection),
        book_popularity_repository=PostgreSQLBookPopularityRepository(connection),
        book_metadata_repository=PostgreSQLBookMetadataRepository(connection),
    )


def test_seed_runner_persists_books_popularity_and_metadata_via_postgresql(
    postgres_connection: psycopg.Connection, sample_path: Path
) -> None:
    context = _build_context(postgres_connection)

    exit_code = main(["--sample-path", str(sample_path)], application_context=context)

    assert exit_code == 0
    book = context.get_book_by_isbn_use_case.execute("9780132350884")
    assert book is not None
    assert book.title.value == "Clean Code"
    assert book.author.value == "Robert C. Martin"

    popularity = context.book_popularity_repository.get_by_book_id(book.id)
    assert popularity is not None
    assert popularity.loan_count == 120

    metadata = context.book_metadata_repository.get_by_book_id(book.id)
    assert metadata is not None
    assert metadata.publisher == "Prentice Hall"
    assert metadata.cover_url == "https://example.test/covers/clean-code.jpg"
    assert metadata.published_date == "2008"


def test_seed_runner_is_idempotent_on_rerun(
    postgres_connection: psycopg.Connection, sample_path: Path
) -> None:
    context = _build_context(postgres_connection)

    first_exit_code = main(["--sample-path", str(sample_path)], application_context=context)
    assert first_exit_code == 0
    books_after_first_run = context.book_repository.list_all()
    assert len(books_after_first_run) == len(_SAMPLE_RECORDS)

    second_exit_code = main(["--sample-path", str(sample_path)], application_context=context)
    assert second_exit_code == 0

    books_after_second_run = context.book_repository.list_all()
    # No duplicate rows: re-running with identical data neither grows the
    # catalog nor changes any book's identity.
    assert len(books_after_second_run) == len(_SAMPLE_RECORDS)
    assert {book.id for book in books_after_first_run} == {
        book.id for book in books_after_second_run
    }

    book = context.get_book_by_isbn_use_case.execute("9780441013593")
    assert book is not None
    popularity = context.book_popularity_repository.get_by_book_id(book.id)
    assert popularity is not None
    assert popularity.loan_count == 150


def test_sample_file_data_source_parses_the_real_committed_sample_dataset() -> None:
    """Guards the real fixture's shape, not a copy: the seed script's mapping
    (author-prefix stripping, publication_year -> published_date) must stay
    valid against data/raw/data4library_popular_books_2025_sample.json as it
    is actually committed, not just against this test's own small fixture.
    """
    from readmatch_ai.domain.book_data_source import PopularLoanBooksQuery

    real_sample_path = _REPO_ROOT / "data" / "raw" / "data4library_popular_books_2025_sample.json"
    source = SampleFileBookDataSource(real_sample_path)

    books = source.search_popular_loans(PopularLoanBooksQuery("2025-01-01", "2025-12-31"))

    assert len(books) == 10
    for book in books:
        assert book.isbn13
        assert book.title
        assert book.author
        assert not book.author.startswith("지은이")
        assert book.loan_count > 0


def test_default_book_metadata_repository_is_in_memory_when_not_overridden() -> None:
    """Sanity check that ApplicationContext.create() without an explicit
    book_metadata_repository still composes (the default in-memory backend),
    so scripts/seed_demo_data.py works out of the box against the default
    in-memory configuration too, not only against PostgreSQL.
    """
    context = ApplicationContext.create()
    assert isinstance(context.book_metadata_repository, InMemoryBookMetadataRepository)
