from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import threadpoolctl
from implicit.als import AlternatingLeastSquares

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction

_DEFAULT_FACTORS = 32
_DEFAULT_ITERATIONS = 15
_DEFAULT_RANDOM_STATE = 42


@dataclass(frozen=True)
class AlsModel:
    """A trained implicit-ALS model's factor matrices, keyed by domain identity.

    Deliberately holds only plain numpy arrays and id tuples — not the
    third-party `implicit` model object itself — so it can be persisted with
    plain numpy serialization (see AlsModelFileStore) independent of that
    library's own (de)serialization.
    """

    user_ids: tuple[UserId, ...]
    book_ids: tuple[BookId, ...]
    user_factors: np.ndarray
    item_factors: np.ndarray

    @property
    def is_empty(self) -> bool:
        return not self.user_ids or not self.book_ids


def train_als_model(
    interactions: list[UserBookInteraction],
    *,
    factors: int = _DEFAULT_FACTORS,
    iterations: int = _DEFAULT_ITERATIONS,
    random_state: int = _DEFAULT_RANDOM_STATE,
) -> AlsModel:
    """Train an implicit-ALS model from raw interaction signals.

    Training (the algorithm, its hyperparameters, the third-party library)
    is entirely an Infrastructure concern — the Domain defines only
    UserBookInteraction/UserBookInteractionRepository, never this function.
    Returns an empty AlsModel (no fit() call) when there are no interactions
    to train on, e.g. a fresh deployment with no recorded interactions yet.
    """
    if not interactions:
        return AlsModel(
            user_ids=(),
            book_ids=(),
            user_factors=np.zeros((0, factors)),
            item_factors=np.zeros((0, factors)),
        )

    user_ids = tuple(
        sorted({interaction.user_id for interaction in interactions}, key=lambda u: str(u.value))
    )
    book_ids = tuple(
        sorted({interaction.book_id for interaction in interactions}, key=lambda b: str(b.value))
    )
    user_index = {user_id: index for index, user_id in enumerate(user_ids)}
    book_index = {book_id: index for index, book_id in enumerate(book_ids)}

    rows = [user_index[interaction.user_id] for interaction in interactions]
    cols = [book_index[interaction.book_id] for interaction in interactions]
    data = [float(interaction.interaction_count) for interaction in interactions]
    user_items = sp.csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(book_ids)))

    model = AlternatingLeastSquares(
        factors=factors, iterations=iterations, random_state=random_state
    )
    # Multi-threaded BLAS reductions can vary run-to-run; pin to a single
    # thread so a fixed random_state actually reproduces bit-identical
    # factors (also silences implicit's own "OpenBLAS ... severe performance
    # issues" warning about the same threading concern).
    with threadpoolctl.threadpool_limits(1, "blas"):
        model.fit(user_items)

    return AlsModel(
        user_ids=user_ids,
        book_ids=book_ids,
        user_factors=np.asarray(model.user_factors),
        item_factors=np.asarray(model.item_factors),
    )
