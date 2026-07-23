#!/usr/bin/env python3
"""Reproducible demo-data seed runner.

Loads the already-committed Data4Library sample fixture
(`data/raw/data4library_popular_books_2025_sample.json`) through the same
ImportBooksUseCase pipeline scripts/import_books.py uses for the real
Data4Library API -- Book, BookPopularity, and BookMetadata (cover_url,
publisher, published_date) are all persisted via the existing
BookRepository/BookPopularityRepository/BookMetadataRepository ports
(configured backend, e.g. PostgreSQL), never a direct SQL insert. Then
generates an embedding for every seeded book via the existing
GenerateBookEmbeddingUseCase, so the Similar Books/semantic recommendation
section has real data to show.

Safe to run any number of times: ImportBooksUseCase reconciles by ISBN
(new -> imported, unchanged -> left alone, changed -> updated in place) and
every repository write it makes (popularity, metadata) is an upsert keyed
by book_id -- re-running this script is a no-op for row counts, not a
duplicate-accumulating one.

Usage:
    PYTHONPATH=src python3 scripts/seed_demo_data.py
    PYTHONPATH=src python3 scripts/seed_demo_data.py --sample-path path/to/other.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)

_DEFAULT_SAMPLE_PATH = Path("data/raw/data4library_popular_books_2025_sample.json")
_AUTHOR_PREFIX_RE = re.compile(r"^지은이:\s*")

# Only affects which BookPopularity period this run's loan counts are
# recorded under (see _record_popularity); the sample fixture carries no
# per-record date of its own to derive this from instead.
_SEED_PERIOD_START = "2025-01-01"
_SEED_PERIOD_END = "2025-12-31"


class SampleFileBookDataSource(BookDataSource):
    """Reads the committed sample JSON as a BookDataSource.

    Implements the exact same port scripts/import_books.py's
    Data4LibraryBookDataSource does -- ImportBooksUseCase cannot tell this
    apart from a live API response.
    """

    def __init__(self, sample_path: Path) -> None:
        self._sample_path = sample_path

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        records = json.loads(self._sample_path.read_text(encoding="utf-8"))
        return [_to_popular_loan_book(record) for record in records]


def _to_popular_loan_book(record: dict[str, Any]) -> PopularLoanBook:
    author = _AUTHOR_PREFIX_RE.sub("", record.get("authors") or "").strip() or "Unknown"
    published_date = str(record["publication_year"]) if record.get("publication_year") else None
    return PopularLoanBook(
        isbn13=record["isbn13"],
        title=record["title"],
        author=author,
        publisher=record.get("publisher") or "",
        category=record.get("category") or "Uncategorized",
        loan_count=record["loan_count"],
        cover_url=record.get("cover_url") or None,
        published_date=published_date,
        detail_url=record.get("detail_url"),
    )


def main(
    argv: list[str] | None = None,
    *,
    application_context: ApplicationContext | None = None,
    book_data_source: BookDataSource | None = None,
) -> int:
    args = _parse_args(argv)
    context = (
        application_context if application_context is not None else ApplicationContext.create()
    )
    data_source = (
        book_data_source
        if book_data_source is not None
        else SampleFileBookDataSource(args.sample_path)
    )

    use_case = ImportBooksUseCase(
        data_source,
        context.book_repository,
        context.book_popularity_repository,
        context.import_history_repository,
        book_metadata_repository=context.book_metadata_repository,
    )
    result = use_case.execute(PopularLoanBooksQuery(_SEED_PERIOD_START, _SEED_PERIOD_END))

    for book in result.imported + result.updated + result.unchanged:
        context.generate_book_embedding_use_case.execute(str(book.id.value))

    print(
        f"Seeded {len(result.imported)} new, {len(result.updated)} updated, "
        f"{len(result.unchanged)} unchanged book(s) "
        f"({len(result.invalid_records)} invalid, {len(result.failed_records)} failed)."
    )
    for message in result.invalid_records:
        print(f"  invalid: {message}")
    for message in result.failed_records:
        print(f"  failed: {message}")

    return 0 if not result.failed_records else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed the configured BookRepository with the committed Data4Library "
            "sample dataset via the existing ImportBooksUseCase pipeline."
        )
    )
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=_DEFAULT_SAMPLE_PATH,
        help=f"Path to the sample JSON file (default: {_DEFAULT_SAMPLE_PATH}).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
