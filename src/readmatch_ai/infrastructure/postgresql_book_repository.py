from __future__ import annotations

from typing import Any

import psycopg
from psycopg import errors

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_repository import (
    BookNotFoundError,
    BookRepository,
    DuplicateISBNError,
)

_SELECT_COLUMNS = "id, isbn, title, author, category"


class PostgreSQLBookRepository(BookRepository):
    """PostgreSQL adapter for BookRepository.

    Receives an already-open psycopg.Connection (connection lifecycle is a
    composition-root concern, not this adapter's). ISBN uniqueness is
    enforced by the database's UNIQUE constraint (see migrations/); a
    UniqueViolation is translated into the domain-level DuplicateISBNError.
    """

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    @property
    def connection(self) -> psycopg.Connection:
        """The underlying connection -- read-only access for callers that need
        to reuse it (e.g. PostgreSQLPersistenceRuntimeValidator), rather than
        opening a second, redundant one. Never exposes credentials: a
        psycopg.Connection object itself carries no printable secret.
        """
        return self._connection

    def add(self, book: Book) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO books (id, isbn, title, author, category) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (book.id.value, book.isbn.value, book.title.value, book.author.value,
                     book.category.value),
                )
        except errors.UniqueViolation as exc:
            self._connection.rollback()
            raise DuplicateISBNError(f"ISBN already exists: {book.isbn.value}") from exc
        self._connection.commit()

    def get_by_id(self, book_id: BookId) -> Book | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM books WHERE id = %s", (book_id.value,)
            )
            row = cursor.fetchone()
        return self._row_to_book(row) if row is not None else None

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLUMNS} FROM books WHERE isbn = %s", (isbn.value,)
            )
            row = cursor.fetchone()
        return self._row_to_book(row) if row is not None else None

    def list_all(self) -> list[Book]:
        with self._connection.cursor() as cursor:
            # ORDER BY id: PostgreSQL gives no row-order guarantee without
            # one, and callers (the batch embedding pipeline) need a
            # deterministic order across runs.
            cursor.execute(f"SELECT {_SELECT_COLUMNS} FROM books ORDER BY id")
            rows = cursor.fetchall()
        return [self._row_to_book(row) for row in rows]

    def update(self, book: Book) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE books SET isbn = %s, title = %s, author = %s, category = %s "
                    "WHERE id = %s",
                    (book.isbn.value, book.title.value, book.author.value, book.category.value,
                     book.id.value),
                )
                found = cursor.rowcount > 0
        except errors.UniqueViolation as exc:
            self._connection.rollback()
            raise DuplicateISBNError(f"ISBN already exists: {book.isbn.value}") from exc

        if not found:
            self._connection.rollback()
            raise BookNotFoundError(f"Book not found: {book.id}")
        self._connection.commit()

    def remove(self, book_id: BookId) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute("DELETE FROM books WHERE id = %s", (book_id.value,))
            found = cursor.rowcount > 0

        if not found:
            self._connection.rollback()
            raise BookNotFoundError(f"Book not found: {book_id}")
        self._connection.commit()

    @staticmethod
    def _row_to_book(row: tuple[Any, ...]) -> Book:
        id_value, isbn_value, title_value, author_value, category_value = row
        return Book(
            id=BookId(id_value),
            isbn=ISBN(isbn_value),
            title=Title(title_value),
            author=Author(author_value),
            category=Category(category_value),
        )
