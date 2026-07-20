from __future__ import annotations

from dataclasses import dataclass, field

from readmatch_ai.application.book_import_mapper import map_to_book
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_data_source import BookDataSource, PopularLoanBooksQuery
from readmatch_ai.domain.book_repository import BookRepository, DuplicateISBNError


@dataclass(frozen=True)
class ImportBooksResult:
    imported: list[Book] = field(default_factory=list)
    skipped_duplicate_isbns: list[str] = field(default_factory=list)


class ImportBooksUseCase:
    """Retrieves popular loan books, maps them to Book, and persists new ones.

    Books whose ISBN already exists in the repository are skipped (not
    treated as a failure) so one duplicate does not abort the whole import.
    """

    def __init__(self, book_data_source: BookDataSource, book_repository: BookRepository) -> None:
        self._book_data_source = book_data_source
        self._book_repository = book_repository

    def execute(self, query: PopularLoanBooksQuery) -> ImportBooksResult:
        source_books = self._book_data_source.search_popular_loans(query)

        imported: list[Book] = []
        skipped_duplicate_isbns: list[str] = []
        for source_book in source_books:
            book = map_to_book(source_book)
            try:
                self._book_repository.add(book)
            except DuplicateISBNError:
                skipped_duplicate_isbns.append(book.isbn.value)
                continue
            imported.append(book)

        return ImportBooksResult(imported=imported, skipped_duplicate_isbns=skipped_duplicate_isbns)
