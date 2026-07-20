from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.infrastructure.postgresql_book_embedding_repository import (
    PostgreSQLBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
_DIMENSIONS = 384


@pytest.fixture(scope="module")
def postgres_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("pgvector/pgvector:pg16") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        connection = psycopg.connect(dsn)
        for migration in (
            "0001_create_books_table.sql",
            "0003_create_book_embeddings_table.sql",
            "0004_add_pgvector_to_book_embeddings.sql",
            "0005_widen_book_embeddings_vector_to_384.sql",
        ):
            connection.execute((_MIGRATIONS_DIR / migration).read_text())
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


def _vector(*head: float) -> tuple[float, ...]:
    """A vector matching the fixed pgvector column width (_DIMENSIONS), zero-padded."""
    return head + (0.0,) * (_DIMENSIONS - len(head))


def _embedding(book_id: BookId, value: float = 0.5) -> BookEmbedding:
    return BookEmbedding(
        book_id=book_id,
        vector=(value,) * _DIMENSIONS,
        model_name="test-model",
        dimensions=_DIMENSIONS,
    )


def _embedding_with_vector(book_id: BookId, vector: tuple[float, ...]) -> BookEmbedding:
    return BookEmbedding(
        book_id=book_id, vector=vector, model_name="test-model", dimensions=_DIMENSIONS
    )


def _assert_embeddings_almost_equal(actual: BookEmbedding | None, expected: BookEmbedding) -> None:
    # pgvector stores components as single-precision floats, so a round-tripped
    # value may differ slightly (float32 precision) from the float64 value saved.
    assert actual is not None
    assert actual.book_id == expected.book_id
    assert actual.model_name == expected.model_name
    assert actual.dimensions == expected.dimensions
    assert actual.vector == pytest.approx(expected.vector, abs=1e-6)


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

    _assert_embeddings_almost_equal(repository.get_by_book_id(book.id), embedding)


def test_save_upserts_existing_book_id(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book = _add_book(postgres_connection)
    repository.save(_embedding(book.id, value=0.1))

    repository.save(_embedding(book.id, value=0.9))

    updated = _embedding(book.id, value=0.9)
    _assert_embeddings_almost_equal(repository.get_by_book_id(book.id), updated)


def test_find_similar_returns_empty_list_when_no_embeddings_stored(
    repository: PostgreSQLBookEmbeddingRepository,
) -> None:
    assert repository.find_similar(_vector(1.0), limit=5) == []


def test_find_similar_ranks_by_cosine_distance_ascending(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    closest = _embedding_with_vector(
        _add_book(postgres_connection, "978-3-16-148410-0").id, _vector(1.0, 0.0)
    )
    middle = _embedding_with_vector(
        _add_book(postgres_connection, "978-0-13-468599-1").id, _vector(0.9, 0.1)
    )
    farthest = _embedding_with_vector(
        _add_book(postgres_connection, "978-0-596-00712-6").id, _vector(0.0, 1.0)
    )
    repository.save(farthest)
    repository.save(closest)
    repository.save(middle)

    result = repository.find_similar(_vector(1.0, 0.0), limit=3)

    assert [embedding.book_id for embedding in result] == [
        closest.book_id,
        middle.book_id,
        farthest.book_id,
    ]


def test_find_similar_truncates_to_limit(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    closest = _embedding_with_vector(
        _add_book(postgres_connection, "978-3-16-148410-0").id, _vector(1.0, 0.0)
    )
    farthest = _embedding_with_vector(
        _add_book(postgres_connection, "978-0-13-468599-1").id, _vector(0.0, 1.0)
    )
    repository.save(farthest)
    repository.save(closest)

    result = repository.find_similar(_vector(1.0, 0.0), limit=1)

    assert [embedding.book_id for embedding in result] == [closest.book_id]


def test_application_context_generates_and_finds_similar_embeddings_via_postgresql(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book_repository = PostgreSQLBookRepository(postgres_connection)
    context = ApplicationContext.create(
        book_repository=book_repository, book_embedding_repository=repository
    )
    book = _add_book(postgres_connection, "978-3-16-148410-0")

    embedding = context.generate_book_embedding_use_case.execute(str(book.id.value))

    assert embedding is not None
    result = context.book_embedding_repository.find_similar(embedding.vector, limit=1)
    assert len(result) == 1
    _assert_embeddings_almost_equal(result[0], embedding)


def test_application_context_generates_semantic_recommendations_via_postgresql(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book_repository = PostgreSQLBookRepository(postgres_connection)
    context = ApplicationContext.create(
        book_repository=book_repository, book_embedding_repository=repository
    )
    source = _add_book(postgres_connection, "978-3-16-148410-0")
    other = Book(
        id=BookId.generate(),
        isbn=ISBN("978-0-13-468599-1"),
        title=Title("Effective Java"),
        author=Author("Joshua Bloch"),
        category=Category("Software Engineering"),
    )
    book_repository.add(other)
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))

    result = context.generate_semantic_recommendation_use_case.execute(
        book_id=str(source.id.value), limit=10
    )

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book.id == other.id
    assert result.recommendation.items[0].source == "semantic"


def test_application_context_generates_hybrid_recommendations_via_postgresql(
    postgres_connection: psycopg.Connection, repository: PostgreSQLBookEmbeddingRepository
) -> None:
    book_repository = PostgreSQLBookRepository(postgres_connection)
    context = ApplicationContext.create(
        book_repository=book_repository, book_embedding_repository=repository
    )
    source = _add_book(postgres_connection, "978-3-16-148410-0")
    other = Book(
        id=BookId.generate(),
        isbn=ISBN("978-0-13-468599-1"),
        title=Title("Effective Java"),
        author=Author("Joshua Bloch"),
        category=Category("Software Engineering"),
    )
    book_repository.add(other)
    context.generate_book_embedding_use_case.execute(str(source.id.value))
    context.generate_book_embedding_use_case.execute(str(other.id.value))
    context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    result = context.generate_hybrid_recommendation_use_case.execute(
        book_id=str(source.id.value), limit=10
    )

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book.id == other.id
    assert result.recommendation.items[0].source == "hybrid"
