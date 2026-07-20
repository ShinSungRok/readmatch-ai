from __future__ import annotations

from typing import Any

import psycopg

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository

_SELECT_COLUMNS = "book_id, vector, model_name, dimensions"


class BookEmbeddingPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting BookEmbedding.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLBookEmbeddingRepository(BookEmbeddingRepository):
    """PostgreSQL adapter for BookEmbeddingRepository.

    Stores the vector as a native PostgreSQL array (no pgvector extension
    yet — that is Sprint 18's responsibility). Receives an already-open
    psycopg.Connection (lifecycle owned by the caller). save() is an atomic
    upsert keyed by book_id, matching InMemoryBookEmbeddingRepository's
    overwrite-latest-signal semantics.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def save(self, embedding: BookEmbedding) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO book_embeddings (book_id, vector, model_name, dimensions) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (book_id) DO UPDATE SET "
                    "vector = EXCLUDED.vector, "
                    "model_name = EXCLUDED.model_name, "
                    "dimensions = EXCLUDED.dimensions",
                    (
                        embedding.book_id.value,
                        list(embedding.vector),
                        embedding.model_name,
                        embedding.dimensions,
                    ),
                )
        except psycopg.Error as exc:
            self._connection.rollback()
            raise BookEmbeddingPersistenceError(str(exc)) from exc
        self._connection.commit()

    def get_by_book_id(self, book_id: BookId) -> BookEmbedding | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM book_embeddings WHERE book_id = %s",
                (book_id.value,),
            )
            row = cursor.fetchone()
        return self._row_to_embedding(row) if row is not None else None

    @staticmethod
    def _row_to_embedding(row: tuple[Any, ...]) -> BookEmbedding:
        book_id_value, vector, model_name, dimensions = row
        return BookEmbedding(
            book_id=BookId(book_id_value),
            vector=tuple(vector),
            model_name=model_name,
            dimensions=dimensions,
        )
