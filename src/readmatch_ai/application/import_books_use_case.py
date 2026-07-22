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
from readmatch_ai.domain.book_repository import (
    BookNotFoundError,
    BookRepository,
    DuplicateISBNError,
)
from readmatch_ai.domain.import_history import ImportHistoryEntry, ImportHistoryRepository


def _default_clock() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@dataclass(frozen=True)
class ImportBooksResult:
    imported: list[Book] = field(default_factory=list)
    updated: list[Book] = field(default_factory=list)
    unchanged: list[Book] = field(default_factory=list)
    invalid_records: list[str] = field(default_factory=list)
    failed_records: list[str] = field(default_factory=list)


class ImportBooksUseCase:
    """Retrieves popular loan books, normalizes them, and reconciles them into the repository.

    Every source record is validated independently: a record that fails
    domain validation (e.g. an invalid ISBN, empty title) is recorded in
    `invalid_records` and skipped, rather than aborting the whole batch.

    Every valid record is reconciled by ISBN and normalized content -- the
    "deterministic reconciliation" this codebase uses in place of a true
    changed-since feed (Data4Library's loanItemSrch endpoint has none):
    - no existing book with that ISBN -> added as new (`imported`).
    - an existing book whose title/author/category all already match the
      incoming (normalized) values -> left untouched (`unchanged`); no
      repository write happens, so re-running identical data is a no-op
      for the Book aggregate itself.
    - an existing book whose title/author/category differ -> updated in
      place, preserving its existing identity/BookId so downstream
      references (recorded popularity, embeddings) stay valid (`updated`).
    This also naturally deduplicates repeated ISBNs within one batch: the
    second occurrence sees the first's freshly-added/updated book as
    "existing".

    A repository-level failure (BookNotFoundError/DuplicateISBNError,
    e.g. a race against a concurrent writer) on one record is caught and
    recorded in `failed_records` rather than aborting the batch -- the same
    resilience already applied to validation failures, extended to
    persistence failures.

    For every valid, successfully reconciled book -- imported, updated, or
    unchanged -- its loan_count is (re)recorded via BookPopularityRepository
    against the Book's real identity, since popularity is a distinct,
    period-scoped signal, not a Book field, and re-importing a period is a
    valid refresh regardless of whether the Book's own fields changed.

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
        unchanged: list[Book] = []
        invalid_records: list[str] = []
        failed_records: list[str] = []
        for source_book in source_books:
            try:
                book = map_to_book(source_book)
            except ValueError as exc:
                invalid_records.append(f"{source_book.isbn13}: {exc}")
                continue

            try:
                self._reconcile(
                    book,
                    source_book,
                    query,
                    imported=imported,
                    updated=updated,
                    unchanged=unchanged,
                )
            except (BookNotFoundError, DuplicateISBNError) as exc:
                failed_records.append(f"{source_book.isbn13}: {exc}")

        self._import_history_repository.record(
            ImportHistoryEntry(
                imported_at=self._clock(),
                period_start=query.start_date,
                period_end=query.end_date,
                imported_count=len(imported),
                updated_count=len(updated),
                unchanged_count=len(unchanged),
                invalid_count=len(invalid_records),
                failed_count=len(failed_records),
            )
        )

        return ImportBooksResult(
            imported=imported,
            updated=updated,
            unchanged=unchanged,
            invalid_records=invalid_records,
            failed_records=failed_records,
        )

    def _reconcile(
        self,
        book: Book,
        source_book: PopularLoanBook,
        query: PopularLoanBooksQuery,
        *,
        imported: list[Book],
        updated: list[Book],
        unchanged: list[Book],
    ) -> None:
        existing_book = self._book_repository.get_by_isbn(book.isbn)
        if existing_book is None:
            self._book_repository.add(book)
            imported.append(book)
            self._record_popularity(book.id, source_book, query)
            return

        if _content_unchanged(existing_book, book):
            unchanged.append(existing_book)
            self._record_popularity(existing_book.id, source_book, query)
            return

        upserted_book = replace(book, id=existing_book.id)
        self._book_repository.update(upserted_book)
        updated.append(upserted_book)
        self._record_popularity(upserted_book.id, source_book, query)

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


def _content_unchanged(existing: Book, incoming: Book) -> bool:
    return (
        existing.title == incoming.title
        and existing.author == incoming.author
        and existing.category == incoming.category
    )
