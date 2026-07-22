from __future__ import annotations

from readmatch_ai.application.book_detail import BookDetail
from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.home_feed import HomeFeedItem


class GetBookDetailUseCase:
    """Retrieves UI-ready detail for a single book, or None if it doesn't exist.

    Reuses the existing GetBookPresentationUseCase (Sprint 39) for the book
    itself and the existing GenerateSemanticRecommendationUseCase for
    similar books -- the same similarity capability every other endpoint
    already uses, not a new one. No ranking/scoring logic of its own.
    """

    def __init__(
        self,
        book_presentation_use_case: GetBookPresentationUseCase,
        semantic_use_case: GenerateSemanticRecommendationUseCase,
    ) -> None:
        self._book_presentation_use_case = book_presentation_use_case
        self._semantic_use_case = semantic_use_case

    def execute(self, book_id: str, limit: int = 12) -> BookDetail | None:
        presentation = self._book_presentation_use_case.execute(book_id)
        if presentation is None:
            return None

        similar_items = self._semantic_use_case.execute(
            book_id=book_id, limit=limit
        ).recommendation.items
        # One batch presentation lookup for every similar book, not one
        # BookMetadataRepository round-trip per item.
        presentations = self._book_presentation_use_case.execute_many(
            [item.book for item in similar_items]
        )
        similar_books = [
            HomeFeedItem(
                book=presentations[str(item.book.id.value)],
                score=item.score,
                source=item.source,
            )
            for item in similar_items
        ]
        return BookDetail(book=presentation, similar_books=similar_books)
