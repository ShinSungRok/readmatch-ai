#!/usr/bin/env python3
"""Executable production data-refresh runner.

Runs the complete recommendation data-refresh pipeline for one period:
sync -> book upsert/change detection -> embedding refresh -> popularity
refresh -> result (see RefreshRecommendationDataUseCase's own docstring
for the staged, partially-recoverable execution model). Orchestration
only, matching scripts/import_books.py and scripts/sync_books.py's own
composition-root boundary -- ApplicationContext cannot fully build this
pipeline itself, since ImportBooksUseCase (which SynchronizeBooksUseCase
wraps) needs a real BookDataSource with no sensible default.

Usage:
    python scripts/refresh_recommendation_data.py \
        --start-date 2024-01-01 --end-date 2024-01-31
"""

from __future__ import annotations

import argparse
import sys

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.application.refresh_recommendation_data_use_case import (
    RefreshRecommendationDataUseCase,
)
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
    synchronize_use_case = SynchronizeBooksUseCase(
        import_use_case, context.sync_checkpoint_repository
    )
    refresh_use_case = RefreshRecommendationDataUseCase(
        synchronize_use_case, context.refresh_book_embeddings_use_case
    )
    result = refresh_use_case.execute(PopularLoanBooksQuery(args.start_date, args.end_date))

    sync = result.synchronization.import_result
    embeddings = result.embedding_refresh
    print(
        f"Sync through {result.synchronization.checkpoint.period_end}: "
        f"created {len(sync.imported)}, updated {len(sync.updated)}, "
        f"unchanged {len(sync.unchanged)}, invalid {len(sync.invalid_records)}, "
        f"failed {len(sync.failed_records)}."
    )
    print(
        f"Embeddings: requested {embeddings.requested}, "
        f"generated {len(embeddings.generated)}, skipped {len(embeddings.skipped)}, "
        f"failed {len(embeddings.failed)}."
    )
    print(f"Popularity refreshed for {len(result.popularity_refreshed_book_ids)} book(s).")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full sync -> embedding refresh -> popularity refresh pipeline."
    )
    parser.add_argument("--start-date", required=True, help="Period start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="Period end date (YYYY-MM-DD)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
