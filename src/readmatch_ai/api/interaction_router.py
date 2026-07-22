from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import (
    InteractionListResponse,
    InteractionRequest,
    InteractionResponse,
)
from readmatch_ai.application.record_interaction_use_case import RecordInteractionInput
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/interactions", tags=["interactions"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]


@router.post(
    "",
    response_model=InteractionResponse,
    status_code=201,
    summary="Record an explicit user interaction",
    description=(
        "Records click/like/dislike/bookmark/read/rating for a user against "
        "a book. `value` is required (1-5) for a rating interaction and "
        "must be omitted for every other type. Recording a state-like "
        "interaction (everything but click) again for the same user/book "
        "replaces any prior value for that type -- idempotent, not "
        "additive. Returns 404 if no book exists with the given id, and "
        "400 for a malformed user/book id, an unknown interaction type, or "
        "an invalid rating value."
    ),
    responses={404: {"description": "No book exists with the given id."}},
)
def record_interaction(
    payload: InteractionRequest, context: _ApplicationContextDependency
) -> InteractionResponse:
    interaction = context.record_interaction_use_case.execute(
        RecordInteractionInput(
            user_id=payload.user_id,
            book_id=payload.book_id,
            interaction_type=payload.interaction_type,
            value=payload.value,
        )
    )
    if interaction is None:
        raise HTTPException(status_code=404, detail=f"No book exists with id '{payload.book_id}'.")
    return InteractionResponse.from_domain(interaction)


@router.delete(
    "",
    status_code=204,
    summary="Clear a previously recorded state-like interaction",
    description=(
        "Removes a like/dislike/bookmark/read/rating for a user/book (e.g. "
        "un-bookmark). A no-op (still 204) if nothing was recorded. "
        "Rejects `click` (event-like: there is no single state to clear)."
    ),
)
def clear_interaction(
    context: _ApplicationContextDependency,
    user_id: Annotated[str, Query()],
    book_id: Annotated[str, Query()],
    interaction_type: Annotated[str, Query()],
) -> Response:
    context.clear_interaction_use_case.execute(user_id, book_id, interaction_type)
    return Response(status_code=204)


@router.get(
    "/{user_id}",
    response_model=InteractionListResponse,
    summary="List a user's recorded interactions",
    description=(
        "Every interaction currently recorded for a user: the latest value "
        "per (book, interaction_type) for state-like types, plus every "
        "individual click event. An unknown-but-well-formed user id "
        "returns an empty list, not an error."
    ),
)
def list_interactions(
    user_id: str, context: _ApplicationContextDependency
) -> InteractionListResponse:
    interactions = context.get_user_interactions_use_case.execute(user_id)
    return InteractionListResponse.from_domain(interactions)
