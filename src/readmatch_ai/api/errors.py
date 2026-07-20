from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Translate Domain/Application input errors into a consistent 400 response.

    Application/Domain layers raise plain ValueError for invalid input (e.g.
    a malformed book id, per the existing GetBookByIdUseCase/GenerateSemantic-
    RecommendationUseCase convention) — without this handler FastAPI would
    surface those as an opaque 500. FastAPI's own request-validation errors
    (missing/malformed query params) already produce a structured 422 and
    need no handler here.
    """

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
