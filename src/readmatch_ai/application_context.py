from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.get_book_by_id_use_case import GetBookByIdUseCase
from readmatch_ai.application.get_book_by_isbn_use_case import GetBookByISBNUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookUseCase
from readmatch_ai.domain.book_repository import BookRepository


@dataclass(frozen=True)
class ApplicationContext:
    """Composition root holding the wired BookRepository and Book use cases."""

    book_repository: BookRepository
    register_book_use_case: RegisterBookUseCase
    get_book_by_id_use_case: GetBookByIdUseCase
    get_book_by_isbn_use_case: GetBookByISBNUseCase
