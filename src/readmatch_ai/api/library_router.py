from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import PersonalLibraryResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/library", tags=["library"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]


@router.get(
    "/{user_id}",
    response_model=PersonalLibraryResponse,
    summary="Personal library",
    description=(
        "A user's personal library, composed from their recorded "
        "interactions: liked, bookmarked, read, rated, and disliked books, "
        "each enriched with presentation metadata. Composes the existing "
        "InteractionRepository and book-presentation use case -- no "
        "duplicate storage. Sections are omitted when empty; an "
        "unknown-but-well-formed user id returns an empty library "
        "(sections: []), not an error."
    ),
)
def get_personal_library(
    user_id: str, context: _ApplicationContextDependency
) -> PersonalLibraryResponse:
    library = context.get_personal_library_use_case.execute(user_id)
    return PersonalLibraryResponse.from_domain(library)
