from __future__ import annotations

from typing import Any

import psycopg

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_metadata import BookMetadata, BookMetadataRepository

_SELECT_COLUMNS = (
    "book_id, publisher, description, cover_url, published_date"
)


class BookMetadataPersistenceError(Exception):
    """Raised when PostgreSQL fails to persist book presentation metadata."""


class PostgreSQLBookMetadataRepository(BookMetadataRepository):
    """PostgreSQL adapter for optional book presentation metadata.

    Receives an already-open psycopg.Connection. Metadata is stored with an
    atomic upsert keyed by book_id, matching the overwrite semantics of the
    in-memory repository.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def record(self, metadata: BookMetadata) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO book_metadata "
                    "(book_id, publisher, description, cover_url, published_date) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (book_id) DO UPDATE SET "
                    "publisher = EXCLUDED.publisher, "
                    "description = EXCLUDED.description, "
                    "cover_url = EXCLUDED.cover_url, "
                    "published_date = EXCLUDED.published_date",
                    (
                        metadata.book_id.value,
                        metadata.publisher,
                        metadata.description,
                        metadata.cover_url,
                        metadata.published_date,
                    ),
                )
        except psycopg.Error as exc:
            self._connection.rollback()
            raise BookMetadataPersistenceError(str(exc)) from exc

        self._connection.commit()

    def get_by_book_id(self, book_id: BookId) -> BookMetadata | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} "
                "FROM book_metadata WHERE book_id = %s",
                (book_id.value,),
            )
            row = cursor.fetchone()

        return self._row_to_metadata(row) if row is not None else None

    def get_by_book_ids(self, book_ids: list[BookId]) -> dict[BookId, BookMetadata]:
        if not book_ids:
            return {}
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} "
                "FROM book_metadata WHERE book_id = ANY(%s)",
                ([book_id.value for book_id in book_ids],),
            )
            rows = cursor.fetchall()
        metadata_list = [self._row_to_metadata(row) for row in rows]
        return {metadata.book_id: metadata for metadata in metadata_list}

    @staticmethod
    def _row_to_metadata(row: tuple[Any, ...]) -> BookMetadata:
        (
            book_id_value,
            publisher,
            description,
            cover_url,
            published_date,
        ) = row

        return BookMetadata(
            book_id=BookId(book_id_value),
            publisher=publisher,
            description=description,
            cover_url=cover_url,
            published_date=published_date,
        )
