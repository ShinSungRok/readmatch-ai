from __future__ import annotations

from typing import Any

import psycopg

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_popularity import BookPopularity, BookPopularityRepository

_SELECT_COLUMNS = "book_id, loan_count, period_start, period_end"


class BookPopularityPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting BookPopularity.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLBookPopularityRepository(BookPopularityRepository):
    """PostgreSQL adapter for BookPopularityRepository.

    Receives an already-open psycopg.Connection (lifecycle owned by the
    caller). record() is an atomic upsert keyed by book_id, matching
    InMemoryBookPopularityRepository's overwrite-latest-signal semantics.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def record(self, popularity: BookPopularity) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO book_popularity (book_id, loan_count, period_start, period_end) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (book_id) DO UPDATE SET "
                    "loan_count = EXCLUDED.loan_count, "
                    "period_start = EXCLUDED.period_start, "
                    "period_end = EXCLUDED.period_end",
                    (
                        popularity.book_id.value,
                        popularity.loan_count,
                        popularity.period_start,
                        popularity.period_end,
                    ),
                )
        except psycopg.Error as exc:
            self._connection.rollback()
            raise BookPopularityPersistenceError(str(exc)) from exc
        self._connection.commit()

    def top_by_loan_count(self, limit: int) -> list[BookPopularity]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM book_popularity "
                "ORDER BY loan_count DESC LIMIT %s",
                (limit,),
            )
            rows = cursor.fetchall()
        return [self._row_to_popularity(row) for row in rows]

    @staticmethod
    def _row_to_popularity(row: tuple[Any, ...]) -> BookPopularity:
        book_id_value, loan_count, period_start, period_end = row
        return BookPopularity(
            book_id=BookId(book_id_value),
            loan_count=loan_count,
            period_start=period_start,
            period_end=period_end,
        )
