from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class UserId:
    """A user's identity. No other User attributes exist yet -- nothing beyond
    identity is needed to record and train on implicit interaction signals.
    """

    value: uuid.UUID

    @classmethod
    def generate(cls) -> UserId:
        return cls(uuid.uuid4())
