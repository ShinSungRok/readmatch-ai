"""Sprint 55 regression tests: the real FastAPI app, served over
GET /recommendations/semantic and /recommendations/hybrid, backed by
PostgreSQLBookRepository + PostgreSQLBookEmbeddingRepository (production
storage) instead of the in-memory defaults -- proving "replace only the
repository implementation" holds at the REST layer, not just the use-case
layer already covered by
tests/infrastructure/test_postgresql_book_embedding_repository.py's
test_application_context_generates_semantic_recommendations_via_postgresql/
test_application_context_generates_hybrid_recommendations_via_postgresql.

SemanticRecommendationEngine, HybridRecommendationEngine, and every REST
schema are exactly the same code exercised by the in-memory-backed tests
elsewhere in this suite -- only which BookRepository/BookEmbeddingRepository
ApplicationContext composes changes here.
"""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.infrastructure.postgresql_book_embedding_repository import (
    PostgreSQLBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


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
            "0002_create_book_popularity_table.sql",
            "0003_create_book_embeddings_table.sql",
            "0004_add_pgvector_to_book_embeddings.sql",
            "0005_widen_book_embeddings_vector_to_384.sql",
            "0007_add_model_version_and_content_hash_to_book_embeddings.sql",
            "0008_configure_hnsw_index_parameters.sql",
        ):
            connection.execute((_MIGRATIONS_DIR / migration).read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def application_context(postgres_connection: psycopg.Connection) -> Iterator[ApplicationContext]:
    context = ApplicationContext.create(
        book_repository=PostgreSQLBookRepository(postgres_connection),
        book_embedding_repository=PostgreSQLBookEmbeddingRepository(postgres_connection),
    )
    yield context
    postgres_connection.execute("TRUNCATE TABLE book_embeddings")
    postgres_connection.execute("TRUNCATE TABLE book_popularity")
    postgres_connection.execute("TRUNCATE TABLE books CASCADE")
    postgres_connection.commit()


@pytest.fixture
def client(application_context: ApplicationContext) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: application_context
    with TestClient(app) as test_client:
        yield test_client


def _add_book(
    postgres_connection: psycopg.Connection, isbn: str, title: str, category: str = "Fiction"
) -> Book:
    book = Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("An Author"),
        category=Category(category),
    )
    PostgreSQLBookRepository(postgres_connection).add(book)
    return book


def test_semantic_recommendations_via_postgresql_preserve_the_empty_fallback(
    postgres_connection: psycopg.Connection, client: TestClient
) -> None:
    """No embedding generated yet -- the existing "no embedding -> empty
    list, not an error" fallback must still hold under the PostgreSQL-backed
    repository, exactly as with the in-memory default.
    """
    source = _add_book(postgres_connection, "978-3-16-148410-0", "Source")

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_semantic_and_hybrid_recommendations_via_postgresql_end_to_end(
    postgres_connection: psycopg.Connection,
    application_context: ApplicationContext,
    client: TestClient,
) -> None:
    source = _add_book(postgres_connection, "978-3-16-148410-0", "Source", "Software Engineering")
    other = _add_book(postgres_connection, "0-306-40615-2", "Other", "Software Engineering")
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))
    application_context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    semantic_response = client.get(f"/recommendations/semantic/{source.id.value}")
    hybrid_response = client.get(
        "/recommendations/hybrid", params={"book_id": str(source.id.value), "limit": 5}
    )

    assert semantic_response.status_code == 200
    semantic_items = semantic_response.json()["items"]
    assert len(semantic_items) == 1
    assert semantic_items[0]["book"]["id"] == str(other.id.value)
    assert semantic_items[0]["source"] == "semantic"

    assert hybrid_response.status_code == 200
    hybrid_item_ids = {item["book"]["id"] for item in hybrid_response.json()["items"]}
    assert str(other.id.value) in hybrid_item_ids
    assert str(source.id.value) not in hybrid_item_ids
