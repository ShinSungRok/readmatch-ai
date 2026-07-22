from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import BookDetailResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(prefix="/books", tags=["books"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]
_LimitQuery = Annotated[
    int, Query(gt=0, le=100, description="Maximum similar books to return.")
]


@router.get(
    "/{book_id}",
    response_model=BookDetailResponse,
    summary="Book detail",
    description=(
        "UI-ready detail for a single book -- presentation metadata (cover, "
        "publisher, description, published date) plus similar books, reusing "
        "the existing semantic-similarity capability. Returns 404 if no book "
        "exists with the given id (a well-formed id is required; a malformed "
        "one responds 400, matching every other book_id path parameter in "
        "this API)."
    ),
    responses={404: {"description": "No book exists with the given id."}},
)
def get_book_detail(
    book_id: str,
    context: _ApplicationContextDependency,
    limit: _LimitQuery = 12,
) -> BookDetailResponse:
    detail = context.get_book_detail_use_case.execute(book_id, limit=limit)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No book exists with id '{book_id}'.")
    return BookDetailResponse.from_domain(detail)
