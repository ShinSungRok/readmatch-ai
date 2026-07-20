from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.als_model import AlsModel


class AlsModelFileStore:
    """Saves/loads a trained AlsModel to/from a local .npz file.

    Plain numpy serialization only (factor arrays + id lists as UUID
    strings) — independent of the `implicit` library's own model
    (de)serialization, so persistence doesn't depend on that library's
    internal format staying stable.
    """

    def exists(self, path: str) -> bool:
        return Path(self._normalize(path)).exists()

    def save(self, model: AlsModel, path: str) -> None:
        normalized = self._normalize(path)
        Path(normalized).parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            normalized,
            user_ids=np.array([str(user_id.value) for user_id in model.user_ids]),
            book_ids=np.array([str(book_id.value) for book_id in model.book_ids]),
            user_factors=model.user_factors,
            item_factors=model.item_factors,
        )

    def load(self, path: str) -> AlsModel:
        with np.load(self._normalize(path)) as data:
            return AlsModel(
                user_ids=tuple(UserId(uuid.UUID(value)) for value in data["user_ids"]),
                book_ids=tuple(BookId(uuid.UUID(value)) for value in data["book_ids"]),
                user_factors=data["user_factors"],
                item_factors=data["item_factors"],
            )

    @staticmethod
    def _normalize(path: str) -> str:
        return path if path.endswith(".npz") else f"{path}.npz"
