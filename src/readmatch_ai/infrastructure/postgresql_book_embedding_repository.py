from __future__ import annotations

from typing import Any

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository

_SELECT_COLUMNS = "book_id, vector, model_name, model_version, dimensions, content_hash"


class BookEmbeddingPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting BookEmbedding.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLBookEmbeddingRepository(BookEmbeddingRepository):
    """PostgreSQL adapter for BookEmbeddingRepository.

    Stores the vector as a pgvector `vector` column and performs similarity
    search via pgvector's cosine distance operator (`<=>`). Receives an
    already-open psycopg.Connection (lifecycle owned by the caller); the
    `vector` extension type is registered on that connection so pgvector
    values convert to/from Python automatically. save() is an atomic upsert
    keyed by book_id, matching InMemoryBookEmbeddingRepository's
    overwrite-latest-signal semantics.

    pgvector stores components as single-precision floats, so a value
    round-tripped through this adapter may differ slightly (float32
    precision) from the float64 value that was saved.

    `model_version`/`content_hash` (Sprint 48, migration 0006) are plain
    TEXT columns alongside the existing `model_name`/`dimensions` -- no new
    indexing or query capability, just the two additional fields
    BookEmbedding now carries.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        register_vector(connection)

    def save(self, embedding: BookEmbedding) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO book_embeddings "
                    "(book_id, vector, model_name, model_version, dimensions, content_hash) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (book_id) DO UPDATE SET "
                    "vector = EXCLUDED.vector, "
                    "model_name = EXCLUDED.model_name, "
                    "model_version = EXCLUDED.model_version, "
                    "dimensions = EXCLUDED.dimensions, "
                    "content_hash = EXCLUDED.content_hash",
                    (
                        embedding.book_id.value,
                        Vector(list(embedding.vector)),
                        embedding.model_name,
                        embedding.model_version,
                        embedding.dimensions,
                        embedding.content_hash,
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

    def find_similar(self, vector: tuple[float, ...], limit: int) -> list[BookEmbedding]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM book_embeddings "
                "ORDER BY vector <=> %s LIMIT %s",
                (Vector(list(vector)), limit),
            )
            rows = cursor.fetchall()
        return [self._row_to_embedding(row) for row in rows]

    @staticmethod
    def _row_to_embedding(row: tuple[Any, ...]) -> BookEmbedding:
        book_id_value, vector, model_name, model_version, dimensions, content_hash = row
        return BookEmbedding(
            book_id=BookId(book_id_value),
            vector=tuple(vector.to_list()),
            model_name=model_name,
            model_version=model_version,
            dimensions=dimensions,
            content_hash=content_hash,
        )
