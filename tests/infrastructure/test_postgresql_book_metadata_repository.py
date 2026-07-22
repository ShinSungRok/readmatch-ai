from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.postgresql_book_metadata_repository import (
    PostgreSQLBookMetadataRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


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
        connection.execute((_MIGRATIONS_DIR / "0010_create_book_metadata_table.sql").read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def book_repository(postgres_connection: psycopg.Connection) -> PostgreSQLBookRepository:
    return PostgreSQLBookRepository(postgres_connection)


@pytest.fixture
def metadata_repository(
    postgres_connection: psycopg.Connection,
) -> Iterator[PostgreSQLBookMetadataRepository]:
    yield PostgreSQLBookMetadataRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE book_metadata")
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


def test_record_and_get_by_book_id(
    book_repository: PostgreSQLBookRepository,
    metadata_repository: PostgreSQLBookMetadataRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    metadata = BookMetadata(
        book.id,
        publisher="Prentice Hall",
        description="A classic.",
        cover_url="https://example.com/cover.jpg",
        published_date="2008-08-01",
    )

    metadata_repository.record(metadata)

    assert metadata_repository.get_by_book_id(book.id) == metadata


def test_get_by_book_id_returns_none_when_never_recorded(
    book_repository: PostgreSQLBookRepository,
    metadata_repository: PostgreSQLBookMetadataRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")

    assert metadata_repository.get_by_book_id(book.id) is None


def test_record_upserts_existing_book_id(
    book_repository: PostgreSQLBookRepository,
    metadata_repository: PostgreSQLBookMetadataRepository,
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    metadata_repository.record(BookMetadata(book.id, publisher="Old"))

    metadata_repository.record(BookMetadata(book.id, publisher="New"))

    assert metadata_repository.get_by_book_id(book.id) == BookMetadata(book.id, publisher="New")


def test_get_by_book_ids_returns_only_recorded_entries_in_one_round_trip(
    book_repository: PostgreSQLBookRepository,
    metadata_repository: PostgreSQLBookMetadataRepository,
) -> None:
    recorded_book = _add_book(book_repository, "978-3-16-148410-0")
    unrecorded_book = _add_book(book_repository, "0-306-40615-2")
    metadata = BookMetadata(recorded_book.id, publisher="Publisher")
    metadata_repository.record(metadata)

    result = metadata_repository.get_by_book_ids([recorded_book.id, unrecorded_book.id])

    assert result == {recorded_book.id: metadata}


def test_get_by_book_ids_returns_empty_dict_for_empty_input(
    metadata_repository: PostgreSQLBookMetadataRepository,
) -> None:
    assert metadata_repository.get_by_book_ids([]) == {}
