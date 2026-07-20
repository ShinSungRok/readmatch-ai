from fastapi.testclient import TestClient

from readmatch_ai.api.main import create_app


def test_default_app_wires_a_working_application_context_via_lifespan() -> None:
    """No dependency override here: proves create_app()'s own lifespan-built
    ApplicationContext.create() (the real default composition, in-memory
    backend) serves a request end-to-end, not just the test-overridden path
    every other API test exercises.
    """
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/recommendations/popularity")

    assert response.status_code == 200
    assert response.json() == {"items": []}
