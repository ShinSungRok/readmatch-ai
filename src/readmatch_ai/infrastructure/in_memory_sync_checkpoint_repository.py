from __future__ import annotations

from readmatch_ai.domain.sync_checkpoint import SyncCheckpoint, SyncCheckpointRepository


class InMemorySyncCheckpointRepository(SyncCheckpointRepository):
    """In-process SyncCheckpointRepository adapter backed by a single slot."""

    def __init__(self) -> None:
        self._checkpoint: SyncCheckpoint | None = None

    def get(self) -> SyncCheckpoint | None:
        return self._checkpoint

    def advance(self, checkpoint: SyncCheckpoint) -> None:
        self._checkpoint = checkpoint
