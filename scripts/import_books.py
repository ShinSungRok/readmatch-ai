#!/usr/bin/env python3
"""Executable production import runner.

Retrieves popular loan books from a BookDataSource and persists them
through the BookRepository configured via ApplicationContext. This is
orchestration (wiring concrete adapters together) and intentionally lives
outside the Application layer — the Application layer (ImportBooksUseCase)
has no knowledge of which BookDataSource or BookRepository backend is used.

Usage:
    python scripts/import_books.py --start-date 2024-01-01 --end-date 2024-01-31
"""

from __future__ import annotations

import argparse
import sys

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
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

    use_case = ImportBooksUseCase(data_source, context.book_repository, popularity_repository)
    result = use_case.execute(PopularLoanBooksQuery(args.start_date, args.end_date))

    print(
        f"Imported {len(result.imported)} book(s); "
        f"skipped {len(result.skipped_duplicate_isbns)} duplicate ISBN(s)."
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import popular loan books into the configured BookRepository."
    )
    parser.add_argument("--start-date", required=True, help="Period start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="Period end date (YYYY-MM-DD)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
