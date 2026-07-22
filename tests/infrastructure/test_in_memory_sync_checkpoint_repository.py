from readmatch_ai.domain.sync_checkpoint import SyncCheckpoint
from readmatch_ai.infrastructure.in_memory_sync_checkpoint_repository import (
    InMemorySyncCheckpointRepository,
)


def test_get_returns_none_when_never_advanced() -> None:
    repository = InMemorySyncCheckpointRepository()

    assert repository.get() is None


def test_advance_then_get_returns_the_recorded_checkpoint() -> None:
    repository = InMemorySyncCheckpointRepository()
    checkpoint = SyncCheckpoint(period_end="2024-01-31", synced_at="2024-02-01T00:00:00+00:00")

    repository.advance(checkpoint)

    assert repository.get() == checkpoint


def test_advance_replaces_the_previous_checkpoint() -> None:
    repository = InMemorySyncCheckpointRepository()
    repository.advance(
        SyncCheckpoint(period_end="2024-01-31", synced_at="2024-02-01T00:00:00+00:00")
    )

    repository.advance(
        SyncCheckpoint(period_end="2024-02-29", synced_at="2024-03-01T00:00:00+00:00")
    )

    assert repository.get() == SyncCheckpoint(
        period_end="2024-02-29", synced_at="2024-03-01T00:00:00+00:00"
    )
