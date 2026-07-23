from __future__ import annotations

import uuid
from dataclasses import dataclass

from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.preference_signal_repository import PreferenceSignalRepository
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class RecordPreferenceSignalInput:
    user_id: str
    signal_type: str
    value: str


class RecordPreferenceSignalUseCase:
    """Records a user behavior signal that is not scoped to a single book.

    Malformed input (invalid user id, unknown signal type, or a blank
    value) raises ValueError -- translated to HTTP 400 by the existing
    global handler (see api.errors), the same convention
    RecordInteractionUseCase already follows. There is no book to check
    existence of, unlike RecordInteractionUseCase.
    """

    def __init__(self, repository: PreferenceSignalRepository) -> None:
        self._repository = repository

    def execute(self, input_data: RecordPreferenceSignalInput) -> UserPreferenceSignal:
        signal = UserPreferenceSignal(
            user_id=UserId(uuid.UUID(input_data.user_id)),
            signal_type=PreferenceSignalType(input_data.signal_type),
            value=input_data.value.strip(),
        )
        self._repository.record(signal)
        return signal
