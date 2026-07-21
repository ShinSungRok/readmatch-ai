import dataclasses

import pytest
from fastapi import FastAPI

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.health_check_service import HealthCheckService
from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.deployment_validation import (
    DEPLOYMENT_VALIDATION_SUCCEEDED,
    ContainerRuntimeValidator,
    DeploymentDiagnostic,
    RuntimeEnvironmentSummary,
)
from readmatch_ai.domain.health import ComponentCheck, HealthStatus, ReadinessStatus
from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class _UnhealthyHealthCheckService(HealthCheckService):
    def check(self) -> HealthStatus:
        return HealthStatus(
            healthy=False, checks=(ComponentCheck(name="process", available=False),)
        )


class _NotReadyReadinessCheckService(ReadinessCheckService):
    def __init__(self) -> None:
        pass

    def check(self) -> ReadinessStatus:
        return ReadinessStatus(
            ready=False,
            checks=(ComponentCheck(name="book_repository", available=False, detail="down"),),
        )


class _RaisingRecommendationEngine(RecommendationEngine):
    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        raise RuntimeError("boom")


def _app_with_context(context: ApplicationContext) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    return app


def test_validate_reports_valid_for_a_healthy_default_application() -> None:
    result = ContainerRuntimeValidator().validate()

    assert result.valid is True
    assert result.checked_components == ("startup", "health", "readiness", "api")


def test_validate_reports_startup_configuration_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    result = ContainerRuntimeValidator().validate()

    assert result.valid is False
    assert result.checked_components == ("startup",)
    assert result.violations[0].code == "startup_configuration_invalid"
    assert result.violations[0].component == "startup"


def test_validate_reports_an_unhealthy_health_endpoint() -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, health_check_service=_UnhealthyHealthCheckService()
    )
    validator = ContainerRuntimeValidator(
        app_factory=lambda: _app_with_context(broken_context)
    )

    result = validator.validate()

    assert result.valid is False
    health_violations = [v for v in result.violations if v.component == "health"]
    assert len(health_violations) == 1
    assert health_violations[0].code == "health_endpoint_unhealthy"
    assert "process" in health_violations[0].message


def test_validate_reports_a_not_ready_readiness_endpoint() -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, readiness_check_service=_NotReadyReadinessCheckService()
    )
    validator = ContainerRuntimeValidator(
        app_factory=lambda: _app_with_context(broken_context)
    )

    result = validator.validate()

    assert result.valid is False
    readiness_violations = [v for v in result.violations if v.component == "readiness"]
    assert len(readiness_violations) == 1
    assert readiness_violations[0].code == "readiness_endpoint_unhealthy"
    assert "book_repository" in readiness_violations[0].message


def test_validate_reports_an_unavailable_api_endpoint() -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context,
        get_recommendations_use_case=GetRecommendationsUseCase(_RaisingRecommendationEngine()),
    )
    validator = ContainerRuntimeValidator(
        app_factory=lambda: _app_with_context(broken_context)
    )

    result = validator.validate()

    assert result.valid is False
    api_violations = [v for v in result.violations if v.component == "api"]
    assert len(api_violations) == 1
    assert api_violations[0].code == "api_endpoint_unavailable"


def test_validate_still_checks_health_and_readiness_when_only_api_is_broken() -> None:
    """A broken recommendation endpoint must not prevent health/readiness
    from still being checked -- all three are independent, and a deployment
    validator should report every independent problem it finds.
    """
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context,
        get_recommendations_use_case=GetRecommendationsUseCase(_RaisingRecommendationEngine()),
    )
    validator = ContainerRuntimeValidator(
        app_factory=lambda: _app_with_context(broken_context)
    )

    result = validator.validate()

    assert result.checked_components == ("startup", "health", "readiness", "api")
    assert not any(v.component in ("health", "readiness") for v in result.violations)


def test_validate_is_deterministic_across_repeated_calls() -> None:
    validator = ContainerRuntimeValidator()

    first = validator.validate()
    second = validator.validate()

    assert first == second


def test_runtime_environment_summary_reflects_a_valid_run() -> None:
    result = ContainerRuntimeValidator().validate()

    summary = RuntimeEnvironmentSummary.build(result)

    assert summary.valid is True
    assert summary.mode == "development"
    assert summary.violation_count == 0
    assert summary.checked_components == result.checked_components


def test_runtime_environment_summary_reports_mode_even_after_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    result = ContainerRuntimeValidator().validate()
    summary = RuntimeEnvironmentSummary.build(result)

    assert summary.valid is False
    assert summary.mode == "production"


def test_deployment_diagnostic_defaults_to_no_violations() -> None:
    diagnostic = DeploymentDiagnostic(category=DEPLOYMENT_VALIDATION_SUCCEEDED, message="ok")

    assert diagnostic.violations == ()
