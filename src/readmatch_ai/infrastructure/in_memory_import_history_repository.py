from __future__ import annotations

from readmatch_ai.domain.import_history import ImportHistoryEntry, ImportHistoryRepository


class InMemoryImportHistoryRepository(ImportHistoryRepository):
    """In-process ImportHistoryRepository adapter backed by a list."""

    def __init__(self) -> None:
        self._entries: list[ImportHistoryEntry] = []

    def record(self, entry: ImportHistoryEntry) -> None:
        self._entries.append(entry)

    def list_all(self) -> list[ImportHistoryEntry]:
        return list(self._entries)
