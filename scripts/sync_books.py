#!/usr/bin/env python3
"""Executable production incremental-synchronization runner.

Retrieves popular loan books from a BookDataSource and reconciles them
through the BookRepository configured via ApplicationContext (via
ImportBooksUseCase), then advances the configured SyncCheckpointRepository
once reconciliation succeeds. Orchestration only -- SynchronizeBooksUseCase
itself has no knowledge of which BookDataSource/BookRepository/
SyncCheckpointRepository backend is used; see scripts/import_books.py's own
docstring for why this composition lives here rather than in
ApplicationContext.

Usage:
    python scripts/sync_books.py --start-date 2024-01-01 --end-date 2024-01-31
"""

from __future__ import annotations

import argparse
import sys

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.application.synchronize_books_use_case import SynchronizeBooksUseCase
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_data_source import BookDataSource, PopularLoanBooksQuery
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.infrastructure.data4library_book_data_source import Data4LibraryBookDataSource


def main(
    argv: list[str] | None = None,
    *,
    book_data_source: BookDataSource | None = None,
    application_context: ApplicationContext | None = None,
    book_popularity_repository: BookPopularityRepository | None = None,
) -> int:
    args = _parse_args(argv)
    context = (
        application_context if application_context is not None else ApplicationContext.create()
    )
    data_source = (
        book_data_source if book_data_source is not None else Data4LibraryBookDataSource()
    )
    popularity_repository = (
        book_popularity_repository
        if book_popularity_repository is not None
        else context.book_popularity_repository
    )

    import_use_case = ImportBooksUseCase(
        data_source,
        context.book_repository,
        popularity_repository,
        context.import_history_repository,
        book_metadata_repository=context.book_metadata_repository,
    )
    sync_use_case = SynchronizeBooksUseCase(import_use_case, context.sync_checkpoint_repository)
    result = sync_use_case.execute(PopularLoanBooksQuery(args.start_date, args.end_date))

    r = result.import_result
    print(
        f"Synchronized through {result.checkpoint.period_end}: "
        f"created {len(r.imported)}, updated {len(r.updated)}, "
        f"unchanged {len(r.unchanged)}, invalid {len(r.invalid_records)}, "
        f"failed {len(r.failed_records)}."
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incrementally synchronize the BookRepository against a BookDataSource."
    )
    parser.add_argument("--start-date", required=True, help="Period start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="Period end date (YYYY-MM-DD)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
