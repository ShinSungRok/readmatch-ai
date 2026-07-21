import pytest

from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class _FakeRecommendationEngine(RecommendationEngine):
    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        return RecommendationResult(recommendation=Recommendation(items=[]))


class _FailingBookRepository(BookRepository):
    def add(self, book: object) -> None:
        raise NotImplementedError

    def get_by_id(self, book_id: BookId) -> None:
        raise RuntimeError("db connection string: postgresql://user:pass@host/db")

    def get_by_isbn(self, isbn: object) -> None:
        raise NotImplementedError

    def update(self, book: object) -> None:
        raise NotImplementedError

    def remove(self, book_id: BookId) -> None:
        raise NotImplementedError


def _engines() -> dict[str, RecommendationEngine]:
    return {"popularity": _FakeRecommendationEngine()}


def test_check_reports_ready_when_repository_and_engines_are_available() -> None:
    service = ReadinessCheckService(InMemoryBookRepository(), _engines())

    status = service.check()

    assert status.ready is True
    assert all(check.available for check in status.checks)


def test_check_reports_not_ready_when_a_recommendation_engine_is_missing() -> None:
    service = ReadinessCheckService(
        InMemoryBookRepository(), {"popularity": None}  # type: ignore[dict-item]
    )

    status = service.check()

    assert status.ready is False
    composition_check = next(
        check for check in status.checks if check.name == "recommendation_composition"
    )
    assert composition_check.available is False
    assert "popularity" in (composition_check.detail or "")


def test_check_reports_not_ready_when_the_book_repository_is_unavailable() -> None:
    service = ReadinessCheckService(_FailingBookRepository(), _engines())

    status = service.check()

    assert status.ready is False
    repository_check = next(check for check in status.checks if check.name == "book_repository")
    assert repository_check.available is False
    assert repository_check.detail == "RuntimeError while checking repository availability"
    # Never leak the underlying exception message (which may embed
    # connection details) into the readiness detail.
    assert "postgresql://" not in (repository_check.detail or "")


def test_check_reports_not_ready_when_configuration_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "not-a-real-backend")
    service = ReadinessCheckService(InMemoryBookRepository(), _engines())

    status = service.check()

    assert status.ready is False
    configuration_check = next(check for check in status.checks if check.name == "configuration")
    assert configuration_check.available is False
