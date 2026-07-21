from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.schemas import HealthResponse, ReadinessResponse
from readmatch_ai.application_context import ApplicationContext

router = APIRouter(tags=["observability"])

_ApplicationContextDependency = Annotated[ApplicationContext, Depends(get_application_context)]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health",
    description=(
        "Is this process itself operating normally? A lightweight, dependency-free "
        "self-check -- distinct from GET /readiness, which probes external dependencies. "
        "Returns HTTP 503 (instead of 200) when unhealthy."
    ),
)
def get_health(context: _ApplicationContextDependency, response: Response) -> HealthResponse:
    status = context.health_check_service.check()
    if not status.healthy:
        response.status_code = 503
    return HealthResponse.from_domain(status)


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    summary="Application readiness",
    description=(
        "Are this instance's required runtime dependencies currently available to serve "
        "requests -- configuration, the book repository, and recommendation engine "
        "composition? Returns HTTP 503 (instead of 200) when not ready."
    ),
)
def get_readiness(
    context: _ApplicationContextDependency, response: Response
) -> ReadinessResponse:
    status = context.readiness_check_service.check()
    if not status.ready:
        response.status_code = 503
    return ReadinessResponse.from_domain(status)
