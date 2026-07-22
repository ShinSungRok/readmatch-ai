from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportHistoryEntry:
    """A record of one completed import run, for audit/statistics purposes.

    period_start/period_end mirror PopularLoanBooksQuery's own date format;
    imported_at is a timestamp string supplied by the caller (see
    ImportBooksUseCase's injected clock) rather than computed here, keeping
    this a plain, deterministic value object.
    """

    imported_at: str
    period_start: str
    period_end: str
    imported_count: int
    updated_count: int
    invalid_count: int


class ImportHistoryRepository(ABC):
    """Port for recording and querying the audit trail of import runs."""

    @abstractmethod
    def record(self, entry: ImportHistoryEntry) -> None:
        """Append one completed import run's statistics."""

    @abstractmethod
    def list_all(self) -> list[ImportHistoryEntry]:
        """Return every recorded import run, oldest first."""
