from __future__ import annotations

import psycopg

from readmatch_ai.domain.sync_checkpoint import SyncCheckpoint, SyncCheckpointRepository


class SyncCheckpointPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting a SyncCheckpoint.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLSyncCheckpointRepository(SyncCheckpointRepository):
    """PostgreSQL adapter for SyncCheckpointRepository.

    Backed by a single-row table (id fixed to 1 via a CHECK constraint) --
    there is exactly one checkpoint for this process's one BookDataSource,
    matching InMemorySyncCheckpointRepository's own single-slot semantics.
    advance() is an atomic upsert of that one row.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def get(self) -> SyncCheckpoint | None:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT period_end, synced_at FROM sync_checkpoint WHERE id = 1")
            row = cursor.fetchone()
        if row is None:
            return None
        period_end, synced_at = row
        return SyncCheckpoint(period_end=period_end, synced_at=synced_at)

    def advance(self, checkpoint: SyncCheckpoint) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sync_checkpoint (id, period_end, synced_at) "
                    "VALUES (1, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "period_end = EXCLUDED.period_end, synced_at = EXCLUDED.synced_at",
                    (checkpoint.period_end, checkpoint.synced_at),
                )
        except psycopg.Error as exc:
            self._connection.rollback()
            raise SyncCheckpointPersistenceError(str(exc)) from exc
        self._connection.commit()
