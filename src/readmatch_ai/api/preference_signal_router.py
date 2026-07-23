from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import PreferenceSignalRequest, PreferenceSignalResponse
from readmatch_ai.application.record_preference_signal_use_case import (
    RecordPreferenceSignalInput,
)
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/preference-signals", tags=["preferences"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]


@router.post(
    "",
    response_model=PreferenceSignalResponse,
    status_code=201,
    summary="Record a user behavior signal not scoped to a single book",
    description=(
        "Records an onboarding category choice (`category_interest`) or a submitted search "
        "query (`search`) for a user -- inputs to the User Preference Profile "
        "(GET /preferences/{user_id}). Book-scoped events (a book detail view, a click from "
        "search results or a recommendation row, a like/bookmark/rating/...) are recorded "
        "through the existing POST /interactions instead. 400 for a malformed user id, an "
        "unknown signal type, or a blank value."
    ),
)
def record_preference_signal(
    payload: PreferenceSignalRequest, context: _ApplicationContextDependency
) -> PreferenceSignalResponse:
    signal = context.record_preference_signal_use_case.execute(
        RecordPreferenceSignalInput(
            user_id=payload.user_id,
            signal_type=payload.signal_type,
            value=payload.value,
        )
    )
    return PreferenceSignalResponse.from_domain(signal)
