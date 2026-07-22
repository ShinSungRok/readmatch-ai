from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SyncCheckpoint:
    """The furthest point up to which incremental synchronization has completed.

    period_end mirrors PopularLoanBooksQuery's own date format -- the
    natural cursor for this source, since Data4Library's loanItemSrch
    endpoint has no separate changed-since parameter (see
    SynchronizeBooksUseCase's own docstring for how reconciliation
    compensates for that). synced_at is a timestamp string supplied by the
    caller's injected clock, matching ImportHistoryEntry's own convention.
    """

    period_end: str
    synced_at: str


class SyncCheckpointRepository(ABC):
    """Port for tracking the last successfully completed synchronization point."""

    @abstractmethod
    def get(self) -> SyncCheckpoint | None:
        """Return the most recently advanced checkpoint, or None if never synced."""

    @abstractmethod
    def advance(self, checkpoint: SyncCheckpoint) -> None:
        """Record a new checkpoint, replacing any previous one."""
