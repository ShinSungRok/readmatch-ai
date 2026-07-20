from __future__ import annotations

from fastapi import Request

from readmatch_ai.application_context import ApplicationContext


def get_application_context(request: Request) -> ApplicationContext:
    """Return the ApplicationContext built once at app startup (see api.main's lifespan).

    Overridden in tests via app.dependency_overrides to inject a
    test-controlled ApplicationContext instead.
    """
    context: ApplicationContext = request.app.state.application_context
    return context
