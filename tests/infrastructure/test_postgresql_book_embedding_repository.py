from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.infrastructure.postgresql_book_embedding_repository import (
    PostgreSQLBookEmbeddingRepository,
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
        connection.execute((_MIGRATIONS_DIR / "0003_create_book_embeddings_table.sql").read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def repository(
    postgres_connection: psycopg.Connection,
) -> Iterator[PostgreSQLBookEmbeddingRepository]:
    yield PostgreSQLBookEmbeddingRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE book_embeddings")
    postgres_connection.execute("TRUNCATE TABLE books CASCADE")
    postgres_connection.commit()


def _add_book(postgres_connection: psycopg.Connection, isbn: str = "978-3-16-148410-0") -> Book:
    book = Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )
    PostgreSQLBookRepository(postgres_connection).add(book)
    return book


def _embedding(book_id: BookId, value: float = 0.5) -> BookEmbedding:
    return BookEmbedding(book_id=book_id, vector=(value,), model_name="test-model", dimensions=1)


def test_get_by_book_id_missing_returns_none(
    repository: PostgreSQLBookEmbeddingRepository,
) -> None:
    assert repository.get_by_book_id(BookId.generate()) is None


def test_save_and_get_by_book_id(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book = _add_book(postgres_connection)
    embedding = _embedding(book.id)

    repository.save(embedding)

    assert repository.get_by_book_id(book.id) == embedding


def test_save_upserts_existing_book_id(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book = _add_book(postgres_connection)
    repository.save(_embedding(book.id, value=0.1))

    repository.save(_embedding(book.id, value=0.9))

    assert repository.get_by_book_id(book.id) == _embedding(book.id, value=0.9)
