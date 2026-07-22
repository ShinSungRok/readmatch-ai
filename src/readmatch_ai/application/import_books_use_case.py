from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from readmatch_ai.application.book_import_mapper import map_to_book
from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.domain.book_popularity import BookPopularity, BookPopularityRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.import_history import ImportHistoryEntry, ImportHistoryRepository


def _default_clock() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@dataclass(frozen=True)
class ImportBooksResult:
    imported: list[Book] = field(default_factory=list)
    updated: list[Book] = field(default_factory=list)
    invalid_records: list[str] = field(default_factory=list)


class ImportBooksUseCase:
    """Retrieves popular loan books, normalizes them, and upserts them into the repository.

    Every source record is validated independently: a record that fails
    domain validation (e.g. an invalid ISBN, empty title) is recorded in
    `invalid_records` and skipped, rather than aborting the whole batch.

    Every valid record is upserted by ISBN: a book already in the
    repository has its fields updated in place (preserving its existing
    identity/BookId, so downstream references such as recorded popularity
    or embeddings stay valid); a book not yet seen is added as new -- this
    also naturally deduplicates repeated ISBNs within one batch, since the
    second occurrence sees the first's freshly-added book as "existing".

    For every valid book seen in this import -- newly added or updated --
    its loan_count is (re)recorded via BookPopularityRepository against the
    Book's real identity, since popularity is a distinct, period-scoped
    signal, not a Book field, and re-importing a period is a valid refresh.

    One ImportHistoryEntry summarizing the whole run is recorded at the end
    via ImportHistoryRepository, timestamped by the injected `clock` (real
    time in production, a fixed function in tests) so the recorded audit
    trail stays deterministic without needing to mock wall-clock time.
    """

    def __init__(
        self,
        book_data_source: BookDataSource,
        book_repository: BookRepository,
        book_popularity_repository: BookPopularityRepository,
        import_history_repository: ImportHistoryRepository,
        clock: Callable[[], str] = _default_clock,
    ) -> None:
        self._book_data_source = book_data_source
        self._book_repository = book_repository
        self._book_popularity_repository = book_popularity_repository
        self._import_history_repository = import_history_repository
        self._clock = clock

    def execute(self, query: PopularLoanBooksQuery) -> ImportBooksResult:
        source_books = self._book_data_source.search_popular_loans(query)

        imported: list[Book] = []
        updated: list[Book] = []
        invalid_records: list[str] = []
        for source_book in source_books:
            try:
                book = map_to_book(source_book)
            except ValueError as exc:
                invalid_records.append(f"{source_book.isbn13}: {exc}")
                continue

            existing_book = self._book_repository.get_by_isbn(book.isbn)
            if existing_book is not None:
                upserted_book = replace(book, id=existing_book.id)
                self._book_repository.update(upserted_book)
                updated.append(upserted_book)
                self._record_popularity(upserted_book.id, source_book, query)
            else:
                self._book_repository.add(book)
                imported.append(book)
                self._record_popularity(book.id, source_book, query)

        self._import_history_repository.record(
            ImportHistoryEntry(
                imported_at=self._clock(),
                period_start=query.start_date,
                period_end=query.end_date,
                imported_count=len(imported),
                updated_count=len(updated),
                invalid_count=len(invalid_records),
            )
        )

        return ImportBooksResult(
            imported=imported, updated=updated, invalid_records=invalid_records
        )

    def _record_popularity(
        self, book_id: BookId, source_book: PopularLoanBook, query: PopularLoanBooksQuery
    ) -> None:
        self._book_popularity_repository.record(
            BookPopularity(
                book_id=book_id,
                loan_count=source_book.loan_count,
                period_start=query.start_date,
                period_end=query.end_date,
            )
        )
