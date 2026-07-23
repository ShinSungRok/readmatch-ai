from __future__ import annotations

import uuid

from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.home_feed import HomeFeedItem
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


class GenerateRerankedRecommendationUseCase:
    """Retrieves re-ranked hybrid recommendations, presentation-ready.

    The RecommendationEngine injected here is expected to be a
    RerankedRecommendationEngine wrapping the Hybrid engine, but this use
    case has no knowledge of that -- it only depends on the
    RecommendationEngine port, same as every other recommendation use case.
    `user_id` is optional here (the personalized API endpoint is what
    enforces "always has a user" by making it a required path parameter);
    `book_id` is optional too, so a source book can still be blended in.

    Unlike its sibling use cases (GetRecommendationsUseCase,
    GenerateHybridRecommendationUseCase, ...), this one additionally
    enriches every ranked item via the existing GetBookPresentationUseCase
    (Sprint 39) -- one execute_many() batch call, not one lookup per item
    -- and returns presentation-ready HomeFeedItems (reusing the existing
    DTO GetHomeFeedUseCase/GetBookDetailUseCase already return, rather than
    inventing a new one), so GET /recommendations/personalized/{user_id}
    returns the same book payload shape (cover_url/publisher/description/
    published_date included) as the Home Feed and Book Detail's "Similar
    books" row -- previously it serialized the bare Domain Book, which the
    frontend's BookCard cannot render a cover from. No ranking/scoring
    logic changed: this only translates the engine's already-produced,
    already-ordered result.
    """

    def __init__(
        self,
        recommendation_engine: RecommendationEngine,
        book_presentation_use_case: GetBookPresentationUseCase,
    ) -> None:
        self._recommendation_engine = recommendation_engine
        self._book_presentation_use_case = book_presentation_use_case

    def execute(
        self, limit: int, book_id: str | None = None, user_id: str | None = None
    ) -> list[HomeFeedItem]:
        query = RecommendationQuery(
            limit=limit,
            book_id=BookId(uuid.UUID(book_id)) if book_id is not None else None,
            user_id=UserId(uuid.UUID(user_id)) if user_id is not None else None,
        )
        items = self._recommendation_engine.recommend(query).recommendation.items
        presentations = self._book_presentation_use_case.execute_many(
            [item.book for item in items]
        )
        return [
            HomeFeedItem(
                book=presentations[str(item.book.id.value)], score=item.score, source=item.source
            )
            for item in items
        ]
