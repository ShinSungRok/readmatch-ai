import pytest

from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.persistence_validation import (
    PersistenceRuntimeValidator,
    PersistenceValidationResult,
    PersistenceValidationViolation,
)
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


class _StubPersistenceRuntimeValidator(PersistenceRuntimeValidator):
    def __init__(self, result: PersistenceValidationResult) -> None:
        self._result = result
        self.call_count = 0

    def validate(self) -> PersistenceValidationResult:
        self.call_count += 1
        return self._result


class _FailingBookRepository(BookRepository):
    def add(self, book: object) -> None:
        raise NotImplementedError

    def get_by_id(self, book_id: BookId) -> None:
        raise RuntimeError("db connection string: postgresql://user:pass@host/db")

    def get_by_isbn(self, isbn: object) -> None:
        raise NotImplementedError

    def list_all(self) -> list[Book]:
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


def test_check_reports_not_ready_when_production_mode_uses_an_in_memory_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sprint 32: ReadinessCheckService's configuration check is extended
    (not duplicated) to also apply ApplicationConfigurationValidator's
    business rules, not just per-field parsing -- so a live drift into an
    unsafe production/in_memory combination is caught the same way an
    unknown backend already was.
    """
    monkeypatch.setenv("APPLICATION_MODE", "production")
    service = ReadinessCheckService(InMemoryBookRepository(), _engines())

    status = service.check()

    assert status.ready is False
    configuration_check = next(check for check in status.checks if check.name == "configuration")
    assert configuration_check.available is False
    assert "production" in (configuration_check.detail or "")


def test_check_preserves_healthy_readiness_when_configuration_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)
    service = ReadinessCheckService(InMemoryBookRepository(), _engines())

    status = service.check()

    assert status.ready is True
    assert all(check.available for check in status.checks)


# --- Sprint 33: persistence runtime integration ---


def test_check_omits_the_persistence_runtime_check_when_no_validator_is_provided() -> None:
    service = ReadinessCheckService(InMemoryBookRepository(), _engines())

    status = service.check()

    check_names = {check.name for check in status.checks}
    assert "persistence_runtime" not in check_names
    assert check_names == {"configuration", "book_repository", "recommendation_composition"}


def test_check_reports_ready_when_persistence_runtime_is_valid() -> None:
    validator = _StubPersistenceRuntimeValidator(
        PersistenceValidationResult(violations=(), checked_components=("connectivity",))
    )
    service = ReadinessCheckService(InMemoryBookRepository(), _engines(), validator)

    status = service.check()

    assert status.ready is True
    persistence_check = next(
        check for check in status.checks if check.name == "persistence_runtime"
    )
    assert persistence_check.available is True
    assert persistence_check.detail is None


def test_check_reports_not_ready_when_persistence_runtime_is_invalid() -> None:
    validator = _StubPersistenceRuntimeValidator(
        PersistenceValidationResult(
            violations=(
                PersistenceValidationViolation(
                    code="pgvector_extension_missing",
                    component="pgvector_extension",
                    message="The pgvector 'vector' extension is not installed",
                ),
            ),
            checked_components=("connectivity", "required_tables", "pgvector_extension"),
        )
    )
    service = ReadinessCheckService(InMemoryBookRepository(), _engines(), validator)

    status = service.check()

    assert status.ready is False
    persistence_check = next(
        check for check in status.checks if check.name == "persistence_runtime"
    )
    assert persistence_check.available is False
    assert "pgvector_extension" in (persistence_check.detail or "")


def test_check_calls_the_persistence_validator_fresh_on_every_call() -> None:
    validator = _StubPersistenceRuntimeValidator(
        PersistenceValidationResult(violations=(), checked_components=("connectivity",))
    )
    service = ReadinessCheckService(InMemoryBookRepository(), _engines(), validator)

    service.check()
    service.check()

    assert validator.call_count == 2


def test_check_is_deterministic_with_a_persistence_validator() -> None:
    validator = _StubPersistenceRuntimeValidator(
        PersistenceValidationResult(violations=(), checked_components=("connectivity",))
    )
    service = ReadinessCheckService(InMemoryBookRepository(), _engines(), validator)

    first = service.check()
    second = service.check()

    assert first == second
