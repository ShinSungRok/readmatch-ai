from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from readmatch_ai.api.errors import register_exception_handlers
from readmatch_ai.api.health_router import router as health_router
from readmatch_ai.api.recommendations_router import router as recommendations_router
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.config import CorsConfig


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.application_context = ApplicationContext.create()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application (a fresh instance per call, for test isolation)."""
    app = FastAPI(
        title="ReadMatch AI Recommendation API",
        description="Popularity, semantic, and hybrid book recommendations.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(CorsConfig.from_env().allowed_origins),
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(recommendations_router)
    return app


app = create_app()
