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
_UserIdQuery = Annotated[
    str | None,
    Query(
        description="Optional user to personalize with (adds the ALS collaborative-filtering "
        "signal)."
    ),
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
    summary="Hybrid (popularity + semantic + ALS) recommendations",
    description=(
        "Combines popularity, semantic, and ALS collaborative-filtering signals. book_id and "
        "user_id are both optional: omitting either degrades gracefully to whichever signals "
        "remain active (at minimum, popularity)."
    ),
)
def get_hybrid_recommendations(
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 10,
    book_id: _BookIdQuery = None,
    user_id: _UserIdQuery = None,
) -> RecommendationResponse:
    result = context.generate_hybrid_recommendation_use_case.execute(
        limit=limit, book_id=book_id, user_id=user_id
    )
    return RecommendationResponse.from_domain(result)


@router.get(
    "/personalized/{user_id}",
    response_model=RecommendationResponse,
    summary="Personalized recommendations (Hybrid ranking + re-ranking) for a user",
    description=(
        "Routes the given user through RecommendationEngine -> Hybrid ranking -> "
        "RecommendationReranker (popularity-penalty, novelty-boost, and MMR-diversity "
        "policies). book_id is optional: providing it also blends semantic similarity to that "
        "book. An unknown-but-well-formed user_id, a user with no interactions, or missing ALS "
        "training data all degrade gracefully to whichever signals remain active -- the "
        "existing engine/reranker fallback behaviour, unchanged here -- rather than a 404."
    ),
)
def get_personalized_recommendations(
    user_id: str,
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 10,
    book_id: _BookIdQuery = None,
) -> RecommendationResponse:
    result = context.generate_reranked_recommendation_use_case.execute(
        limit=limit, book_id=book_id, user_id=user_id
    )
    return RecommendationResponse.from_domain(result)
