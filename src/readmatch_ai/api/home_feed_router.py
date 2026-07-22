from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import HomeFeedResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(tags=["home-feed"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]
_LimitQuery = Annotated[int, Query(gt=0, le=100, description="Maximum items per section.")]


@router.get(
    "/home-feed",
    response_model=HomeFeedResponse,
    summary="Consolidated recommendation home feed",
    description=(
        "One application-level response for the recommendation home page: an "
        "optional hero (the top popularity pick) plus zero or more titled "
        "sections -- popular books, blended (hybrid) picks, books similar to "
        "the hero, and per-category rows -- each book enriched with "
        "presentation metadata (cover, publisher, description, published "
        "date). Composes the existing popularity/hybrid/semantic "
        "recommendation use cases and the book-presentation use case; "
        "introduces no new ranking or scoring logic. Returns an empty feed "
        "(hero: null, sections: []) if there are no books yet, rather than "
        "an error."
    ),
)
def get_home_feed(
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 12,
) -> HomeFeedResponse:
    feed = context.get_home_feed_use_case.execute(limit=limit)
    return HomeFeedResponse.from_domain(feed)
