from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from readmatch_ai.domain.sync_checkpoint import SyncCheckpoint
from readmatch_ai.infrastructure.postgresql_sync_checkpoint_repository import (
    PostgreSQLSyncCheckpointRepository,
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
        connection.execute((_MIGRATIONS_DIR / "0009_create_sync_checkpoint_table.sql").read_text())
        connection.commit()
        yield connection
        connection.close()


@pytest.fixture
def repository(
    postgres_connection: psycopg.Connection,
) -> Iterator[PostgreSQLSyncCheckpointRepository]:
    yield PostgreSQLSyncCheckpointRepository(postgres_connection)
    postgres_connection.execute("TRUNCATE TABLE sync_checkpoint")
    postgres_connection.commit()


def test_get_returns_none_when_never_advanced(
    repository: PostgreSQLSyncCheckpointRepository,
) -> None:
    assert repository.get() is None


def test_advance_then_get_returns_the_recorded_checkpoint(
    repository: PostgreSQLSyncCheckpointRepository,
) -> None:
    checkpoint = SyncCheckpoint(period_end="2024-01-31", synced_at="2024-02-01T00:00:00+00:00")

    repository.advance(checkpoint)

    assert repository.get() == checkpoint


def test_advance_replaces_the_previous_checkpoint(
    repository: PostgreSQLSyncCheckpointRepository,
) -> None:
    repository.advance(
        SyncCheckpoint(period_end="2024-01-31", synced_at="2024-02-01T00:00:00+00:00")
    )

    repository.advance(
        SyncCheckpoint(period_end="2024-02-29", synced_at="2024-03-01T00:00:00+00:00")
    )

    assert repository.get() == SyncCheckpoint(
        period_end="2024-02-29", synced_at="2024-03-01T00:00:00+00:00"
    )
