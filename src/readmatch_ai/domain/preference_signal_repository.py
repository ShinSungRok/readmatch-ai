from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.preference_signal import UserPreferenceSignal
from readmatch_ai.domain.user import UserId


class PreferenceSignalRepository(ABC):
    """Port for persisting and retrieving UserPreferenceSignals.

    Every signal is event-like (see UserPreferenceSignal): there is no
    `clear`, mirroring InteractionRepository's CLICK handling -- a category
    selection or a search is a fact about something that happened, not a
    toggleable state.
    """

    @abstractmethod
    def record(self, signal: UserPreferenceSignal) -> None:
        """Append a new signal. Never overwrites a prior one."""

    @abstractmethod
    def list_by_user(self, user_id: UserId) -> list[UserPreferenceSignal]:
        """Return every signal recorded for a user, oldest first (recording order)."""
