from __future__ import annotations

import uuid

from readmatch_ai.domain.preference_signal import PreferenceSignalType
from readmatch_ai.domain.preference_signal_repository import PreferenceSignalRepository
from readmatch_ai.domain.user import UserId


class ClearPreferenceSignalUseCase:
    """Removes every previously recorded signal of one type for a user
    (e.g. resetting onboarding category choices).

    A no-op if none were recorded -- clearing is safe to call repeatedly.
    Malformed input (invalid user id or unknown signal type) raises
    ValueError, translated to HTTP 400 by the existing global handler (see
    api.errors), the same convention ClearInteractionUseCase already
    follows.
    """

    def __init__(self, preference_signal_repository: PreferenceSignalRepository) -> None:
        self._preference_signal_repository = preference_signal_repository

    def execute(self, user_id: str, signal_type: str) -> None:
        self._preference_signal_repository.clear(
            UserId(uuid.UUID(user_id)), PreferenceSignalType(signal_type)
        )
