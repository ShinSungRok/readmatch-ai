from __future__ import annotations

import math

from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine

_SOURCE = "semantic"


class SemanticRecommendationEngine(RecommendationEngine):
    """RecommendationEngine ranking books by embedding similarity to a source book.

    Reads only from BookEmbeddingRepository and BookRepository (both already
    persisted) — never generates an embedding at recommendation time. The
    source book itself is excluded from the results; an embedding whose Book
    can no longer be found is skipped rather than failing the whole
    recommendation, mirroring PopularityRecommendationEngine's join behavior.
    """

    def __init__(
        self,
        book_embedding_repository: BookEmbeddingRepository,
        book_repository: BookRepository,
    ) -> None:
        self._book_embedding_repository = book_embedding_repository
        self._book_repository = book_repository

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        if query.book_id is None:
            raise ValueError("SemanticRecommendationEngine requires RecommendationQuery.book_id")

        source_embedding = self._book_embedding_repository.get_by_book_id(query.book_id)
        if source_embedding is None:
            return RecommendationResult(recommendation=Recommendation(items=[]))

        # Fetch one extra candidate since the source book's own embedding is
        # typically its own closest match and must be excluded below.
        candidates = self._book_embedding_repository.find_similar(
            source_embedding.vector, limit=query.limit + 1
        )

        items: list[RecommendationItem] = []
        for candidate in candidates:
            if candidate.book_id == query.book_id:
                continue
            if len(items) >= query.limit:
                break
            book = self._book_repository.get_by_id(candidate.book_id)
            if book is None:
                continue
            score = self._cosine_similarity(source_embedding.vector, candidate.vector)
            items.append(RecommendationItem(book=book, score=score, source=_SOURCE))

        return RecommendationResult(recommendation=Recommendation(items=items))

    @staticmethod
    def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
