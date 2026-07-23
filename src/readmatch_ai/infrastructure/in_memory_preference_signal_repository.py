from __future__ import annotations

from readmatch_ai.domain.preference_signal import UserPreferenceSignal
from readmatch_ai.domain.preference_signal_repository import PreferenceSignalRepository
from readmatch_ai.domain.user import UserId


class InMemoryPreferenceSignalRepository(PreferenceSignalRepository):
    """In-process PreferenceSignalRepository adapter.

    Every signal is appended to a single list (event-like, never
    overwritten), mirroring InMemoryInteractionRepository's CLICK-event
    half exactly.
    """

    def __init__(self) -> None:
        self._signals: list[UserPreferenceSignal] = []

    def record(self, signal: UserPreferenceSignal) -> None:
        self._signals.append(signal)

    def list_by_user(self, user_id: UserId) -> list[UserPreferenceSignal]:
        return [signal for signal in self._signals if signal.user_id == user_id]
