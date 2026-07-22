from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.infrastructure.postgresql_book_repository import PostgreSQLBookRepository
from readmatch_ai.infrastructure.postgresql_persistence_runtime_validator import (
    PostgreSQLPersistenceRuntimeValidator,
    validate_postgresql_persistence,
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _apply_migrations(connection: psycopg.Connection, names: tuple[str, ...]) -> None:
    for name in names:
        connection.execute((_MIGRATIONS_DIR / name).read_text())
    connection.commit()


def _dsn(container: PostgresContainer) -> str:
    return (
        f"postgresql://{container.username}:{container.password}"
        f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
        f"/{container.dbname}"
    )


@pytest.fixture(scope="module")
def full_schema_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("pgvector/pgvector:pg16") as container:
        connection = psycopg.connect(_dsn(container))
        _apply_migrations(
            connection,
            (
                "0001_create_books_table.sql",
                "0002_create_book_popularity_table.sql",
                "0003_create_book_embeddings_table.sql",
                "0004_add_pgvector_to_book_embeddings.sql",
                "0005_widen_book_embeddings_vector_to_384.sql",
                "0006_create_user_book_interactions_table.sql",
                "0007_add_model_version_and_content_hash_to_book_embeddings.sql",
                "0008_configure_hnsw_index_parameters.sql",
            ),
        )
        yield connection
        connection.close()


@pytest.fixture(scope="module")
def missing_tables_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("postgres:16-alpine") as container:
        connection = psycopg.connect(_dsn(container))
        _apply_migrations(connection, ("0001_create_books_table.sql",))
        yield connection
        connection.close()


@pytest.fixture(scope="module")
def no_extension_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("postgres:16-alpine") as container:
        connection = psycopg.connect(_dsn(container))
        _apply_migrations(
            connection,
            ("0001_create_books_table.sql", "0003_create_book_embeddings_table.sql"),
        )
        yield connection
        connection.close()


@pytest.fixture(scope="module")
def dimension_mismatch_connection() -> Iterator[psycopg.Connection]:
    with PostgresContainer("pgvector/pgvector:pg16") as container:
        connection = psycopg.connect(_dsn(container))
        _apply_migrations(
            connection,
            (
                "0001_create_books_table.sql",
                "0003_create_book_embeddings_table.sql",
                "0004_add_pgvector_to_book_embeddings.sql",
            ),
        )
        yield connection
        connection.close()


def test_valid_schema_reports_no_violations(full_schema_connection: psycopg.Connection) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(full_schema_connection)

    result = validator.validate()

    assert result.valid is True
    assert result.checked_components == (
        "connectivity",
        "required_tables",
        "pgvector_extension",
        "vector_dimension",
        "vector_index",
    )


def test_valid_schema_result_is_deterministic_across_repeated_calls(
    full_schema_connection: psycopg.Connection,
) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(full_schema_connection)

    first = validator.validate()
    second = validator.validate()

    assert first == second


def test_missing_tables_are_each_reported(missing_tables_connection: psycopg.Connection) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(missing_tables_connection)

    result = validator.validate()

    assert result.valid is False
    missing = {v.component for v in result.violations if v.code == "missing_required_table"}
    assert missing == {"book_popularity", "book_embeddings", "user_book_interactions"}
    # book_embeddings is missing, so the dependent vector checks are skipped
    # rather than cascading into a second, confusing error for the same
    # root cause.
    assert "vector_dimension" not in result.checked_components
    assert "vector_index" not in result.checked_components


def test_missing_pgvector_extension_is_reported(
    no_extension_connection: psycopg.Connection,
) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(no_extension_connection)

    result = validator.validate()

    assert result.valid is False
    codes = {v.code for v in result.violations}
    assert "pgvector_extension_missing" in codes
    # book_embeddings.vector is a plain DOUBLE PRECISION[] column here (no
    # migration 0004 applied), so the vector-dimension check correctly
    # reports it as not a pgvector column at all, rather than a dimension
    # mismatch.
    assert "vector_column_not_a_vector_type" in codes


def test_vector_dimension_mismatch_is_reported(
    dimension_mismatch_connection: psycopg.Connection,
) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(dimension_mismatch_connection)

    result = validator.validate()

    assert result.valid is False
    dimension_violations = [v for v in result.violations if v.code == "vector_dimension_mismatch"]
    assert len(dimension_violations) == 1
    assert "vector(8)" in dimension_violations[0].message
    assert "vector(384)" in dimension_violations[0].message
    # migration 0004 already creates the index at the (wrong) 8-dimension
    # width, so the index itself is present -- isolating this test to the
    # dimension mismatch alone.
    assert not any(v.code == "missing_required_index" for v in result.violations)


def test_missing_required_index_is_reported(full_schema_connection: psycopg.Connection) -> None:
    full_schema_connection.execute("DROP INDEX idx_book_embeddings_vector_cosine")
    full_schema_connection.commit()
    try:
        validator = PostgreSQLPersistenceRuntimeValidator(full_schema_connection)

        result = validator.validate()

        assert result.valid is False
        assert any(v.code == "missing_required_index" for v in result.violations)
    finally:
        full_schema_connection.execute(
            "CREATE INDEX idx_book_embeddings_vector_cosine "
            "ON book_embeddings USING hnsw (vector vector_cosine_ops)"
        )
        full_schema_connection.commit()


def test_custom_expected_dimensions_is_respected(
    full_schema_connection: psycopg.Connection,
) -> None:
    validator = PostgreSQLPersistenceRuntimeValidator(
        full_schema_connection, expected_vector_dimensions=999
    )

    result = validator.validate()

    assert result.valid is False
    assert any(v.code == "vector_dimension_mismatch" for v in result.violations)


def test_validate_postgresql_persistence_reports_unreachable_without_raising() -> None:
    result = validate_postgresql_persistence(
        "postgresql://nouser:nopass@localhost:1/nonexistent"
    )

    assert result.valid is False
    assert result.violations[0].code == "postgresql_unreachable"
    assert result.checked_components == ("connectivity",)


def test_validate_postgresql_persistence_never_leaks_the_url(
    full_schema_connection: psycopg.Connection,
) -> None:
    result = validate_postgresql_persistence(
        "postgresql://nouser:nopass@localhost:1/nonexistent"
    )

    for violation in result.violations:
        assert "nopass" not in violation.message
        assert "nouser" not in violation.message


def test_application_context_readiness_reports_valid_persistence_runtime(
    full_schema_connection: psycopg.Connection,
) -> None:
    repository: BookRepository = PostgreSQLBookRepository(full_schema_connection)
    context = ApplicationContext.create(book_repository=repository)

    status = context.readiness_check_service.check()

    persistence_check = next(
        check for check in status.checks if check.name == "persistence_runtime"
    )
    assert persistence_check.available is True
