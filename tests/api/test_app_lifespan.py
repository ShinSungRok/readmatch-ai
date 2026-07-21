import uuid

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


def test_default_app_serves_explained_personalized_recommendations_via_lifespan() -> None:
    """Sprint 29: proves GET /recommendations/personalized/{user_id}/explained
    works through the real, lifespan-built ApplicationContext.create()
    default composition (RecommendationEngine -> Hybrid ->
    RecommendationReranker -> RecommendationExplainer), not only against a
    test-controlled context.
    """
    app = create_app()

    with TestClient(app) as client:
        response = client.get(f"/recommendations/personalized/{uuid.uuid4()}/explained")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_default_app_serves_personalized_recommendations_via_lifespan() -> None:
    """Sprint 28: proves GET /recommendations/personalized/{user_id} works
    through the real, lifespan-built ApplicationContext.create() default
    composition (RecommendationEngine -> Hybrid -> RecommendationReranker,
    all resolved via the real Composition Root), not only against a
    test-controlled context.
    """
    app = create_app()

    with TestClient(app) as client:
        response = client.get(f"/recommendations/personalized/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"items": []}
