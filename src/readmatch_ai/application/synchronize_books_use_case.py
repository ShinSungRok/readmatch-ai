from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass

from readmatch_ai.application.import_books_use_case import ImportBooksResult, ImportBooksUseCase
from readmatch_ai.domain.book_data_source import PopularLoanBooksQuery
from readmatch_ai.domain.sync_checkpoint import SyncCheckpoint, SyncCheckpointRepository


def _default_clock() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@dataclass(frozen=True)
class SynchronizationResult:
    import_result: ImportBooksResult
    checkpoint: SyncCheckpoint


class SynchronizeBooksUseCase:
    """Incrementally synchronizes the catalog against a BookDataSource.

    Data4Library's loanItemSrch endpoint has no changed-since cursor -- it
    only accepts a start/end date range -- so "incremental" here means
    deterministic reconciliation by ISBN and normalized content
    (ImportBooksUseCase's existing created/updated/unchanged/invalid/failed
    classification), not a true delta feed. Re-running the same period is
    already idempotent because of that reconciliation, independent of
    whether a checkpoint exists at all.

    SyncCheckpointRepository records the period_end this run completed
    through, as an audit/resume marker for callers -- and, critically, the
    checkpoint is advanced only *after* ImportBooksUseCase.execute()
    returns successfully. If the BookDataSource itself raises (e.g. the
    Data4Library API is unreachable after exhausting its own retries), that
    exception propagates unchanged and the checkpoint is left untouched, so
    a caller can safely retry the same period without the checkpoint
    claiming a completion that didn't happen.
    """

    def __init__(
        self,
        import_books_use_case: ImportBooksUseCase,
        sync_checkpoint_repository: SyncCheckpointRepository,
        clock: Callable[[], str] = _default_clock,
    ) -> None:
        self._import_books_use_case = import_books_use_case
        self._sync_checkpoint_repository = sync_checkpoint_repository
        self._clock = clock

    def execute(self, query: PopularLoanBooksQuery) -> SynchronizationResult:
        import_result = self._import_books_use_case.execute(query)
        checkpoint = SyncCheckpoint(period_end=query.end_date, synced_at=self._clock())
        self._sync_checkpoint_repository.advance(checkpoint)
        return SynchronizationResult(import_result=import_result, checkpoint=checkpoint)
