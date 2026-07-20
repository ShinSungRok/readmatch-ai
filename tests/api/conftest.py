from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application_context import ApplicationContext


@pytest.fixture
def application_context() -> ApplicationContext:
    return ApplicationContext.create()


@pytest.fixture
def client(application_context: ApplicationContext) -> Iterator[TestClient]:
    """A TestClient wired to a caller-controlled, in-memory ApplicationContext.

    Overrides get_application_context so requests never trigger the app's
    own lifespan-created context (and never touch a real database).
    """
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: application_context
    with TestClient(app) as test_client:
        yield test_client
