import dataclasses

from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository


class _FailingBookRepository(BookRepository):
    def add(self, book: object) -> None:
        raise NotImplementedError

    def get_by_id(self, book_id: BookId) -> None:
        raise RuntimeError("connection lost")

    def get_by_isbn(self, isbn: object) -> None:
        raise NotImplementedError

    def update(self, book: object) -> None:
        raise NotImplementedError

    def remove(self, book_id: BookId) -> None:
        raise NotImplementedError


def test_health_endpoint_reports_a_healthy_application(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["healthy"] is True
    assert any(check["name"] == "process" for check in body["checks"])


def test_readiness_endpoint_reports_ready_for_a_freshly_created_context(
    client: TestClient,
) -> None:
    response = client.get("/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    check_names = {check["name"] for check in body["checks"]}
    assert check_names == {"configuration", "book_repository", "recommendation_composition"}


def test_readiness_endpoint_reports_the_active_runtime_mode(client: TestClient) -> None:
    response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "development"


def test_readiness_endpoint_returns_503_when_a_dependency_is_unavailable(
    application_context: ApplicationContext,
) -> None:
    degraded_context = dataclasses.replace(
        application_context,
        readiness_check_service=ReadinessCheckService(
            _FailingBookRepository(),
            {"popularity": application_context.recommendation_engine},
        ),
    )
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: degraded_context
    with TestClient(app) as degraded_client:
        response = degraded_client.get("/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    repository_check = next(check for check in body["checks"] if check["name"] == "book_repository")
    assert repository_check["available"] is False
    assert "connection lost" not in (repository_check["detail"] or "")
