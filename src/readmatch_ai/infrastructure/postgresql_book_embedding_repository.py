from __future__ import annotations

from typing import Any, Literal, get_args

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository

_SELECT_COLUMNS = "book_id, vector, model_name, model_version, dimensions, content_hash"

SimilarityMetric = Literal["cosine", "inner_product"]

# pgvector distance operators, both usable with `ORDER BY ... ASC` to get
# most-similar-first: `<=>` is cosine *distance* (1 - cosine similarity);
# `<#>` is *negative* inner product (pgvector's own convention, so smaller
# is still "more similar", matching `<=>`'s convention rather than
# requiring a DESC sort). Selected from this fixed, whitelisted mapping
# (never from caller-provided text), so interpolating the chosen operator
# into the query string below is not a SQL-injection surface.
_DISTANCE_OPERATORS: dict[SimilarityMetric, str] = {"cosine": "<=>", "inner_product": "<#>"}


class BookEmbeddingPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting BookEmbedding.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLBookEmbeddingRepository(BookEmbeddingRepository):
    """PostgreSQL adapter for BookEmbeddingRepository.

    Stores the vector as a pgvector `vector` column. Receives an
    already-open psycopg.Connection (lifecycle owned by the caller); the
    `vector` extension type is registered on that connection so pgvector
    values convert to/from Python automatically. save() is an atomic upsert
    keyed by book_id, matching InMemoryBookEmbeddingRepository's
    overwrite-latest-signal semantics.

    `similarity_metric` (Sprint 53) selects which pgvector distance
    operator find_similar() ranks by: `"cosine"` (the default, and the
    only correct choice for a vector of unknown or non-unit magnitude --
    e.g. DeterministicFakeBookEmbeddingGenerator's digest-derived vectors,
    which are not normalized) or `"inner_product"` (mathematically
    equivalent to cosine ranking *only* for already-unit-normalized
    vectors -- true of SentenceTransformerBookEmbeddingGenerator's output,
    since it calls `encode(..., normalize_embeddings=True)` -- and
    slightly cheaper per query, since it skips the magnitude
    normalization cosine distance performs internally). "Where
    appropriate" per this Sprint's own requirement wording: opt-in, not
    the default, since choosing it incorrectly for non-normalized vectors
    would silently rank by a meaningless metric with no error raised.

    pgvector stores components as single-precision floats, so a value
    round-tripped through this adapter may differ slightly (float32
    precision) from the float64 value that was saved.

    `model_version`/`content_hash` (Sprint 48, migration 0006) are plain
    TEXT columns alongside the existing `model_name`/`dimensions` -- no new
    indexing or query capability, just the two additional fields
    BookEmbedding now carries.
    """

    def __init__(
        self, connection: psycopg.Connection, similarity_metric: SimilarityMetric = "cosine"
    ) -> None:
        if similarity_metric not in _DISTANCE_OPERATORS:
            raise ValueError(
                f"Unknown similarity_metric: {similarity_metric!r} "
                f"(expected one of {get_args(SimilarityMetric)})"
            )
        self._connection = connection
        self._distance_operator = _DISTANCE_OPERATORS[similarity_metric]
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
                f"ORDER BY vector {self._distance_operator} %s LIMIT %s",
                (Vector(list(vector)), limit),
            )
            rows = cursor.fetchall()
        return [self._row_to_embedding(row) for row in rows]

    def delete(self, book_id: BookId) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("DELETE FROM book_embeddings WHERE book_id = %s", (book_id.value,))
        except psycopg.Error as exc:
            self._connection.rollback()
            raise BookEmbeddingPersistenceError(str(exc)) from exc
        self._connection.commit()

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
