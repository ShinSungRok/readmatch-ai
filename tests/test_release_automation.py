import dataclasses

import pytest
from fastapi import FastAPI

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.health_check_service import HealthCheckService
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.deployment_validation import ContainerRuntimeValidator
from readmatch_ai.domain.health import ComponentCheck, HealthStatus
from readmatch_ai.release_automation import (
    RELEASE_VALIDATION_FAILURE,
    RELEASE_VALIDATION_SUCCEEDED,
    ReleaseAutomationService,
    ReleaseDiagnostic,
    ReleaseSummary,
)


class _UnhealthyHealthCheckService(HealthCheckService):
    def check(self) -> HealthStatus:
        return HealthStatus(
            healthy=False, checks=(ComponentCheck(name="process", available=False),)
        )


def _passing_command(name: str = "ok") -> tuple[str, tuple[str, ...]]:
    return (name, ("python3", "-c", "import sys; sys.exit(0)"))


def _failing_command(name: str = "bad", exit_code: int = 1) -> tuple[str, tuple[str, ...]]:
    return (name, ("python3", "-c", f"import sys; sys.exit({exit_code})"))


def _app_with_context(context: ApplicationContext) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    return app


def test_validate_is_valid_for_a_healthy_default_environment() -> None:
    result = ReleaseAutomationService().validate()

    assert result.valid is True
    assert result.checked_stages == ("configuration", "deployment", "operations")


def test_validate_short_circuits_on_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    result = ReleaseAutomationService().validate()

    assert result.valid is False
    assert result.checked_stages == ("configuration",)
    assert result.violations[0].stage == "configuration"
    assert result.violations[0].code == "production_mode_requires_persistent_repository"


def test_validate_skips_persistence_stage_for_the_in_memory_backend() -> None:
    result = ReleaseAutomationService().validate()

    assert "persistence" not in result.checked_stages


def test_validate_includes_persistence_stage_for_the_postgresql_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://nouser:nopass@localhost:1/nonexistent")

    result = ReleaseAutomationService().validate()

    assert "persistence" in result.checked_stages
    assert any(
        v.stage == "persistence" and v.code == "postgresql_unreachable" for v in result.violations
    )


def test_validate_reflects_a_deployment_failure_via_injected_validator() -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, health_check_service=_UnhealthyHealthCheckService()
    )
    service = ReleaseAutomationService(
        deployment_validator=ContainerRuntimeValidator(
            app_factory=lambda: _app_with_context(broken_context)
        )
    )

    result = service.validate()

    assert result.valid is False
    assert any(v.stage == "deployment" for v in result.violations)


def test_validate_reflects_a_non_operational_operations_report_via_injected_context() -> None:
    def _broken_context_factory() -> ApplicationContext:
        context = ApplicationContext.create()
        return dataclasses.replace(context, health_check_service=_UnhealthyHealthCheckService())

    service = ReleaseAutomationService(context_factory=_broken_context_factory)

    result = service.validate()

    assert result.valid is False
    operations_violations = [v for v in result.violations if v.stage == "operations"]
    assert len(operations_violations) == 1
    assert operations_violations[0].code == "operations_report_not_operational"


def test_validate_reflects_an_operations_context_build_failure() -> None:
    def _raising_context_factory() -> ApplicationContext:
        raise RuntimeError("boom")

    service = ReleaseAutomationService(context_factory=_raising_context_factory)

    result = service.validate()

    assert result.valid is False
    operations_violations = [v for v in result.violations if v.stage == "operations"]
    assert len(operations_violations) == 1
    assert operations_violations[0].code == "operations_context_build_failed"


def test_validate_skips_tests_stage_by_default() -> None:
    result = ReleaseAutomationService().validate()

    assert "tests" not in result.checked_stages


def test_validate_runs_tests_stage_when_requested_with_passing_commands() -> None:
    service = ReleaseAutomationService(test_commands=(_passing_command(),))

    result = service.validate(include_tests=True)

    assert "tests" in result.checked_stages
    assert not any(v.stage == "tests" for v in result.violations)


def test_validate_reports_a_failing_test_command() -> None:
    service = ReleaseAutomationService(
        test_commands=(_passing_command("ok"), _failing_command("bad", exit_code=3))
    )

    result = service.validate(include_tests=True)

    assert result.valid is False
    test_violations = [v for v in result.violations if v.stage == "tests"]
    assert len(test_violations) == 1
    assert test_violations[0].code == "bad_failed"
    assert "3" in test_violations[0].message


def test_validate_reports_a_missing_test_executable() -> None:
    service = ReleaseAutomationService(
        test_commands=(("missing", ("this-binary-does-not-exist-anywhere",)),)
    )

    result = service.validate(include_tests=True)

    assert result.valid is False
    assert result.violations[0].code == "missing_command_failed"
    assert result.violations[0].stage == "tests"


def test_validate_is_deterministic_across_repeated_calls() -> None:
    service = ReleaseAutomationService()

    first = service.validate()
    second = service.validate()

    assert first == second


def test_release_summary_reflects_a_valid_result() -> None:
    result = ReleaseAutomationService().validate()

    summary = ReleaseSummary.build(result)

    assert summary.valid is True
    assert summary.mode == "development"
    assert summary.checked_stages == result.checked_stages
    assert summary.violation_count == 0
    assert summary.application_version


def test_release_summary_reflects_an_invalid_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    result = ReleaseAutomationService().validate()
    summary = ReleaseSummary.build(result)

    assert summary.valid is False
    assert summary.violation_count == 1


def test_release_diagnostic_categories_are_distinct() -> None:
    assert RELEASE_VALIDATION_SUCCEEDED != RELEASE_VALIDATION_FAILURE


def test_release_diagnostic_is_a_plain_value_object() -> None:
    diagnostic = ReleaseDiagnostic(category=RELEASE_VALIDATION_SUCCEEDED, message="ok")

    assert diagnostic.category == RELEASE_VALIDATION_SUCCEEDED
    assert diagnostic.message == "ok"
