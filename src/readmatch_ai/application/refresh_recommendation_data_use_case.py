from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.refresh_book_embeddings_use_case import (
    EmbeddingRefreshResult,
    RefreshBookEmbeddingsUseCase,
)
from readmatch_ai.application.synchronize_books_use_case import (
    SynchronizationResult,
    SynchronizeBooksUseCase,
)
from readmatch_ai.domain.book_data_source import PopularLoanBooksQuery


@dataclass(frozen=True)
class DataRefreshResult:
    """The combined result of one end-to-end production data-refresh run."""

    synchronization: SynchronizationResult
    embedding_refresh: EmbeddingRefreshResult
    popularity_refreshed_book_ids: tuple[str, ...]


class RefreshRecommendationDataUseCase:
    """Runs the full recommendation data-refresh pipeline:
    sync -> book upsert/change detection -> embedding refresh -> popularity refresh -> result.

    "book upsert/change detection" is not a separate stage -- it is what
    SynchronizeBooksUseCase's own reconciliation (ImportBooksUseCase,
    Sprint 57-58) already does as part of "sync". Likewise, "popularity
    refresh" is not a second, separate write: ImportBooksUseCase already
    (re)records each reconciled book's loan_count via
    BookPopularityRepository inline, during the sync stage itself, using
    only the loan_count field Data4Library's response actually provides
    (no invented statistics), upserted through the existing
    BookPopularityRepository contract (already idempotent, and already
    distinguishes "never recorded" (`get_by_book_id` returns None) from an
    explicitly recorded zero). Adding a second, standalone
    popularity-recording pass here would duplicate that existing, correct
    behavior -- the "popularity refresh" stage below instead *reports*
    which books had their popularity (re)recorded by the sync stage that
    already ran, so the pipeline's four named stages are all visible in
    the returned result, without re-executing anything.

    Staged, not atomic, partially recoverable: each stage is a separate,
    independently persisted operation, in this fixed order:
      1. SynchronizeBooksUseCase.execute() -- commits book/popularity
         changes per record as it processes them, and advances the sync
         checkpoint only after it returns successfully. If the
         BookDataSource itself raises (e.g. Data4Library is unreachable),
         that exception propagates unchanged from this method too, and
         neither the checkpoint nor the embedding-refresh stage runs --
         nothing from this run claims to have completed. A caller can
         simply retry the same query.
      2. RefreshBookEmbeddingsUseCase.execute() -- runs only if stage 1
         returned. It never raises (a whole-run failure is caught and
         reported via its own `failed` tuple; see its docstring), so this
         method itself does not need to guard it -- but if the embedding
         model/library genuinely fails, stage 1's book/popularity/
         checkpoint changes are already durably committed and are not
         rolled back. This mirrors how ImportBooksUseCase itself already
         behaves (each record is committed as it's processed, not held in
         an all-or-nothing transaction) rather than introducing a new
         atomicity guarantee nothing else in this codebase provides.
    A failed run can always be safely retried: stage 1 is idempotent by
    construction (ISBN + normalized-content reconciliation), and stage 2
    only regenerates what's actually missing or stale.
    """

    def __init__(
        self,
        synchronize_books_use_case: SynchronizeBooksUseCase,
        refresh_book_embeddings_use_case: RefreshBookEmbeddingsUseCase,
    ) -> None:
        self._synchronize_books_use_case = synchronize_books_use_case
        self._refresh_book_embeddings_use_case = refresh_book_embeddings_use_case

    def execute(self, query: PopularLoanBooksQuery) -> DataRefreshResult:
        synchronization = self._synchronize_books_use_case.execute(query)
        embedding_refresh = self._refresh_book_embeddings_use_case.execute()
        import_result = synchronization.import_result
        popularity_refreshed_book_ids = tuple(
            str(book.id.value)
            for book in (
                import_result.imported + import_result.updated + import_result.unchanged
            )
        )
        return DataRefreshResult(
            synchronization=synchronization,
            embedding_refresh=embedding_refresh,
            popularity_refreshed_book_ids=popularity_refreshed_book_ids,
        )
