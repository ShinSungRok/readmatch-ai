from __future__ import annotations

import numpy as np

from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation import (
    ALS_SOURCE,
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository
from readmatch_ai.infrastructure.als_model import AlsModel


class ALSRecommendationEngine(RecommendationEngine):
    """RecommendationEngine backed by a pre-trained implicit-ALS model.

    Purely a lookup/scoring adapter over an already-trained AlsModel;
    training itself (infrastructure.als_model.train_als_model) is a
    separate, batch concern kept out of this class and out of the Domain
    entirely — this engine never retrains, so it reflects a snapshot of
    interactions as of whenever the model it was constructed with was
    trained, not necessarily the repository's current state.
    """

    def __init__(
        self,
        model: AlsModel,
        book_repository: BookRepository,
        user_book_interaction_repository: UserBookInteractionRepository,
    ) -> None:
        self._model = model
        self._book_repository = book_repository
        self._user_book_interaction_repository = user_book_interaction_repository
        self._user_index = {user_id: index for index, user_id in enumerate(model.user_ids)}

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        if query.user_id is None or self._model.is_empty:
            return RecommendationResult(recommendation=Recommendation(items=[]))

        user_index = self._user_index.get(query.user_id)
        if user_index is None:
            return RecommendationResult(recommendation=Recommendation(items=[]))

        already_interacted = {
            interaction.book_id
            for interaction in self._user_book_interaction_repository.list_by_user(query.user_id)
        }
        scores = self._model.item_factors @ self._model.user_factors[user_index]
        ranked_item_indices = np.argsort(scores)[::-1]

        items: list[RecommendationItem] = []
        for item_index in ranked_item_indices:
            if len(items) >= query.limit:
                break
            book_id = self._model.book_ids[item_index]
            if book_id in already_interacted:
                continue
            book = self._book_repository.get_by_id(book_id)
            if book is None:
                continue
            items.append(
                RecommendationItem(
                    book=book,
                    score=float(scores[item_index]),
                    source=ALS_SOURCE,
                    contributing_sources=frozenset({ALS_SOURCE}),
                )
            )

        return RecommendationResult(recommendation=Recommendation(items=items))
