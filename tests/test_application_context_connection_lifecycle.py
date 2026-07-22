"""Regression coverage for a real defect found during Sprint 67 operational
validation: ApplicationContext.create()'s PostgreSQL-backed repositories
must not leave their connection "idle in transaction" after a read.

Reproduced directly against a real, live server: a long-lived process
serving only GET (read) requests left every PostgreSQL repository
connection idle-in-transaction indefinitely (psycopg's non-autocommit
default), which blocks a concurrent DDL statement (e.g. TRUNCATE, a
migration) against the same tables for as long as that process runs, and
holds one of PostgreSQL's limited connection slots for the process's
entire lifetime regardless of read/write activity.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.application_context import ApplicationContext

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_MIGRATIONS = (
    "0001_create_books_table.sql",
    "0002_create_book_popularity_table.sql",
    "0003_create_book_embeddings_table.sql",
    "0004_add_pgvector_to_book_embeddings.sql",
    "0005_widen_book_embeddings_vector_to_384.sql",
    "0006_create_user_book_interactions_table.sql",
    "0007_add_model_version_and_content_hash_to_book_embeddings.sql",
    "0008_configure_hnsw_index_parameters.sql",
    "0009_create_sync_checkpoint_table.sql",
)


@pytest.fixture
def postgres_dsn(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16") as container:
        dsn = (
            f"postgresql://{container.username}:{container.password}"
            f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
            f"/{container.dbname}"
        )
        setup_connection = psycopg.connect(dsn)
        for migration in _MIGRATIONS:
            setup_connection.execute((_MIGRATIONS_DIR / migration).read_text())
        setup_connection.commit()
        setup_connection.close()

        monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
        monkeypatch.setenv("DATABASE_URL", dsn)
        yield dsn


def test_read_only_repository_use_does_not_block_concurrent_ddl(postgres_dsn: str) -> None:
    """A read through ApplicationContext.create()'s own PostgreSQL wiring
    (env-based, the same path api.main's lifespan and every script use --
    not a caller-injected connection) must not leave a lingering,
    lock-holding transaction open afterward.
    """
    context = ApplicationContext.create()

    # A read-only call on every PostgreSQL-backed repository -- mirrors
    # exactly what a live server handling only GET requests does.
    context.book_repository.list_all()
    context.book_popularity_repository.top_by_loan_count(limit=1)
    context.book_embedding_repository.find_similar(tuple([0.0] * 384), limit=1)
    context.user_book_interaction_repository.list_all()

    # A second, independent connection must be able to TRUNCATE the same
    # tables without blocking -- proves no session from the reads above is
    # still "idle in transaction" holding a lock.
    other_connection = psycopg.connect(postgres_dsn)
    try:
        with other_connection.cursor() as cursor:
            cursor.execute("SET lock_timeout = '2s'")
            cursor.execute(
                "TRUNCATE books, book_popularity, book_embeddings, "
                "user_book_interactions, sync_checkpoint RESTART IDENTITY CASCADE"
            )
        other_connection.commit()
    finally:
        other_connection.close()
