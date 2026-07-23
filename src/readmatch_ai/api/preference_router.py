from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import UserPreferenceProfileResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/preferences", tags=["preferences"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]


@router.get(
    "/{user_id}",
    response_model=UserPreferenceProfileResponse,
    summary="A user's aggregated preference profile",
    description=(
        "Favorite categories/authors (from the user's own like/bookmark/read/rating>=4 "
        "books), recent interests (onboarding category choices plus recently viewed/clicked "
        "book categories), recent search terms, and positive/negative book counts -- built "
        "entirely from the user's own recorded interactions and preference signals. An "
        "unknown-but-well-formed user_id, or a user with no qualifying signals yet, returns "
        "an all-empty/zero profile, not an error (the same cold-start convention as "
        "GET /library/{user_id})."
    ),
)
def get_user_preference_profile(
    user_id: str, context: _ApplicationContextDependency
) -> UserPreferenceProfileResponse:
    profile = context.get_user_preference_profile_use_case.execute(user_id)
    return UserPreferenceProfileResponse.from_domain(profile)
