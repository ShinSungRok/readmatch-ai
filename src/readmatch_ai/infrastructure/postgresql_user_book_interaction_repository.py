from __future__ import annotations

from typing import Any

import psycopg

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository

_SELECT_COLUMNS = "user_id, book_id, interaction_count"


class UserBookInteractionPersistenceError(Exception):
    """Raised when a PostgreSQL-specific error occurs persisting UserBookInteraction.

    Kept inside Infrastructure: callers never see a raw psycopg exception.
    """


class PostgreSQLUserBookInteractionRepository(UserBookInteractionRepository):
    """PostgreSQL adapter for UserBookInteractionRepository.

    Receives an already-open psycopg.Connection (lifecycle owned by the
    caller). record() is an atomic upsert keyed by (user_id, book_id),
    matching InMemoryUserBookInteractionRepository's overwrite semantics.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def record(self, interaction: UserBookInteraction) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO user_book_interactions (user_id, book_id, interaction_count) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (user_id, book_id) DO UPDATE SET "
                    "interaction_count = EXCLUDED.interaction_count",
                    (
                        interaction.user_id.value,
                        interaction.book_id.value,
                        interaction.interaction_count,
                    ),
                )
        except psycopg.Error as exc:
            self._connection.rollback()
            raise UserBookInteractionPersistenceError(str(exc)) from exc
        self._connection.commit()

    def list_all(self) -> list[UserBookInteraction]:
        with self._connection.cursor() as cursor:
            cursor.execute(f"SELECT {_SELECT_COLUMNS} FROM user_book_interactions")
            rows = cursor.fetchall()
        return [self._row_to_interaction(row) for row in rows]

    def list_by_user(self, user_id: UserId) -> list[UserBookInteraction]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM user_book_interactions WHERE user_id = %s",
                (user_id.value,),
            )
            rows = cursor.fetchall()
        return [self._row_to_interaction(row) for row in rows]

    @staticmethod
    def _row_to_interaction(row: tuple[Any, ...]) -> UserBookInteraction:
        user_id_value, book_id_value, interaction_count = row
        return UserBookInteraction(
            user_id=UserId(user_id_value),
            book_id=BookId(book_id_value),
            interaction_count=interaction_count,
        )
