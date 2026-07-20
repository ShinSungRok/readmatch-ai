from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import RecommendationResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]
_LimitQuery = Annotated[int, Query(gt=0, le=100, description="Maximum recommendations to return.")]
_BookIdQuery = Annotated[
    str | None, Query(description="Optional source book to blend semantic similarity with.")
]


@router.get(
    "/popularity",
    response_model=RecommendationResponse,
    summary="Popularity-based recommendations",
    description="Ranks books by persisted loan_count, independent of any source book.",
)
def get_popularity_recommendations(
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 10,
) -> RecommendationResponse:
    result = context.get_recommendations_use_case.execute(limit=limit)
    return RecommendationResponse.from_domain(result)


@router.get(
    "/semantic/{book_id}",
    response_model=RecommendationResponse,
    summary="Books semantically similar to a given book",
    description=(
        "Ranks books by embedding similarity to the given source book, excluding it from "
        "the results. Returns an empty list if the source book has no embedding yet."
    ),
)
def get_semantic_recommendations(
    book_id: str,
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 10,
) -> RecommendationResponse:
    result = context.generate_semantic_recommendation_use_case.execute(
        book_id=book_id, limit=limit
    )
    return RecommendationResponse.from_domain(result)


@router.get(
    "/hybrid",
    response_model=RecommendationResponse,
    summary="Hybrid (popularity + semantic) recommendations",
    description=(
        "Combines popularity and semantic signals. book_id is optional: omitting it "
        "degrades gracefully to the popularity signal (no source book to blend with)."
    ),
)
def get_hybrid_recommendations(
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 10,
    book_id: _BookIdQuery = None,
) -> RecommendationResponse:
    result = context.generate_hybrid_recommendation_use_case.execute(limit=limit, book_id=book_id)
    return RecommendationResponse.from_domain(result)
