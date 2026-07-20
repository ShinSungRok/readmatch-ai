from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_repository import BookRepository


@dataclass(frozen=True)
class RegisterBookInput:
    isbn: str
    title: str
    author: str
    category: str


class RegisterBookUseCase:
    """Registers a new Book; duplicate ISBNs are rejected by BookRepository's domain rule."""

    def __init__(self, book_repository: BookRepository) -> None:
        self._book_repository = book_repository

    def execute(self, input_data: RegisterBookInput) -> Book:
        book = Book(
            id=BookId.generate(),
            isbn=ISBN(input_data.isbn),
            title=Title(input_data.title),
            author=Author(input_data.author),
            category=Category(input_data.category),
        )
        self._book_repository.add(book)
        return book
