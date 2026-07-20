from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository
from readmatch_ai.infrastructure.postgresql_user_book_interaction_repository import (
    PostgreSQLUserBookInteractionRepository,
)

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
        connection.execute(
            (_MIGRATIONS_DIR / "0006_create_user_book_interactions_table.sql").read_text()
        )
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def book_repository(postgres_connection: psycopg.Connection) -> PostgreSQLBookRepository:
    return PostgreSQLBookRepository(postgres_connection)


@pytest.fixture
def repository(
    postgres_connection: psycopg.Connection,
) -> Iterator[PostgreSQLUserBookInteractionRepository]:
    yield PostgreSQLUserBookInteractionRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE user_book_interactions")
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


def test_list_all_is_empty_initially(
    repository: PostgreSQLUserBookInteractionRepository,
) -> None:
    assert repository.list_all() == []


def test_record_and_list_all(
    book_repository: PostgreSQLBookRepository, repository: PostgreSQLUserBookInteractionRepository
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    user_id = UserId.generate()
    interaction = UserBookInteraction(user_id=user_id, book_id=book.id, interaction_count=3)

    repository.record(interaction)

    assert repository.list_all() == [interaction]


def test_record_upserts_by_user_and_book(
    book_repository: PostgreSQLBookRepository, repository: PostgreSQLUserBookInteractionRepository
) -> None:
    book = _add_book(book_repository, "978-3-16-148410-0")
    user_id = UserId.generate()
    repository.record(UserBookInteraction(user_id=user_id, book_id=book.id, interaction_count=1))

    repository.record(UserBookInteraction(user_id=user_id, book_id=book.id, interaction_count=9))

    top = repository.list_all()
    assert top == [UserBookInteraction(user_id=user_id, book_id=book.id, interaction_count=9)]


def test_list_by_user_returns_only_that_users_interactions(
    book_repository: PostgreSQLBookRepository, repository: PostgreSQLUserBookInteractionRepository
) -> None:
    book_a = _add_book(book_repository, "978-3-16-148410-0")
    book_b = _add_book(book_repository, "0-306-40615-2")
    user_a, user_b = UserId.generate(), UserId.generate()
    interaction_a = UserBookInteraction(user_id=user_a, book_id=book_a.id, interaction_count=1)
    interaction_b = UserBookInteraction(user_id=user_b, book_id=book_b.id, interaction_count=1)
    repository.record(interaction_a)
    repository.record(interaction_b)

    assert repository.list_by_user(user_a) == [interaction_a]
