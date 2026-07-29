from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.user import UserId


class PreferenceSignalRepository(ABC):
    """Port for persisting and retrieving UserPreferenceSignals."""

    @abstractmethod
    def record(self, signal: UserPreferenceSignal) -> None:
        """Append a new signal. Never overwrites a prior one."""

    @abstractmethod
    def list_by_user(self, user_id: UserId) -> list[UserPreferenceSignal]:
        """Return every signal recorded for a user, oldest first (recording order)."""

    @abstractmethod
    def clear(self, user_id: UserId, signal_type: PreferenceSignalType) -> None:
        """Remove every signal of `signal_type` previously recorded for a user.

        A no-op if none were recorded. Lets a user reset a whole signal type
        (e.g. their onboarding category choices) at once; unlike
        InteractionRepository.clear, there's no per-value key to target a
        single signal by, since UserPreferenceSignal carries no id.
        """
