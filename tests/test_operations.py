import dataclasses
import logging

import pytest

from readmatch_ai.application.health_check_service import HealthCheckService
from readmatch_ai.application.readiness_check_service import ReadinessCheckService
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.health import ComponentCheck, HealthStatus, ReadinessStatus
from readmatch_ai.operations import (
    OPERATIONS_REPORT_DEGRADED,
    OPERATIONS_REPORT_GENERATED,
    OperationsDiagnostic,
    OperationsService,
    RuntimeOperationsSummary,
)


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
            checks=(
                ComponentCheck(
                    name="persistence_runtime", available=False, detail="pgvector missing"
                ),
            ),
        )


def test_generate_report_is_operational_for_a_healthy_default_context() -> None:
    context = ApplicationContext.create()
    service = OperationsService(context)

    report = service.generate_report()

    assert report.operational is True
    assert report.health.healthy is True
    assert report.readiness.ready is True
    assert report.configuration.configuration_valid is True
    assert report.deployment is None


def test_generate_report_reflects_an_unhealthy_health_check() -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, health_check_service=_UnhealthyHealthCheckService()
    )
    service = OperationsService(broken_context)

    report = service.generate_report()

    assert report.operational is False
    assert report.health.healthy is False


def test_generate_report_reflects_a_not_ready_readiness_check_including_persistence() -> None:
    """The readiness check already reflects persistence integration (Sprint
    33) -- OperationsReport must not need its own separate persistence
    field to see this; reading `readiness.checks` is enough.
    """
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, readiness_check_service=_NotReadyReadinessCheckService()
    )
    service = OperationsService(broken_context)

    report = service.generate_report()

    assert report.operational is False
    assert report.readiness.ready is False
    persistence_check = next(
        check for check in report.readiness.checks if check.name == "persistence_runtime"
    )
    assert persistence_check.available is False


def test_generate_report_skips_deployment_check_by_default() -> None:
    context = ApplicationContext.create()
    service = OperationsService(context)

    report = service.generate_report()

    assert report.deployment is None


def test_generate_report_includes_deployment_check_when_requested() -> None:
    context = ApplicationContext.create()
    service = OperationsService(context)

    report = service.generate_report(include_deployment_check=True)

    assert report.deployment is not None
    assert report.deployment.valid is True
    assert report.deployment.checked_components == ("startup", "health", "readiness", "api")
    assert report.operational is True


def test_generate_report_is_deterministic_across_repeated_calls() -> None:
    context = ApplicationContext.create()
    service = OperationsService(context)

    first = service.generate_report()
    second = service.generate_report()

    assert first == second


def test_generate_report_logs_a_generated_diagnostic_when_operational(
    caplog: pytest.LogCaptureFixture,
) -> None:
    context = ApplicationContext.create()
    service = OperationsService(context)

    with caplog.at_level(logging.INFO, logger="readmatch_ai.operations"):
        service.generate_report()

    assert any(
        record.name == "readmatch_ai.operations" and "operational=True" in record.getMessage()
        for record in caplog.records
    )


def test_generate_report_logs_a_degraded_diagnostic_when_not_operational(
    caplog: pytest.LogCaptureFixture,
) -> None:
    context = ApplicationContext.create()
    broken_context = dataclasses.replace(
        context, health_check_service=_UnhealthyHealthCheckService()
    )
    service = OperationsService(broken_context)

    with caplog.at_level(logging.WARNING, logger="readmatch_ai.operations"):
        service.generate_report()

    assert any(
        record.name == "readmatch_ai.operations" and "operational=False" in record.getMessage()
        for record in caplog.records
    )


def test_runtime_operations_summary_reflects_a_valid_report() -> None:
    context = ApplicationContext.create()
    report = OperationsService(context).generate_report()

    summary = RuntimeOperationsSummary.build(report)

    assert summary.operational is True
    assert summary.mode == "development"
    assert summary.healthy is True
    assert summary.ready is True
    assert summary.configuration_valid is True
    assert summary.deployment_valid is None
    assert summary.recommendation_request_count == 0
    assert summary.application_version


def test_runtime_operations_summary_reports_deployment_validity_when_checked() -> None:
    context = ApplicationContext.create()
    report = OperationsService(context).generate_report(include_deployment_check=True)

    summary = RuntimeOperationsSummary.build(report)

    assert summary.deployment_valid is True


def test_runtime_operations_summary_reflects_recommendation_metrics() -> None:
    context = ApplicationContext.create()
    context.get_recommendations_use_case.execute(limit=3)

    report = OperationsService(context).generate_report()
    summary = RuntimeOperationsSummary.build(report)

    assert summary.recommendation_request_count == 1


def test_operations_diagnostic_categories_are_distinct() -> None:
    assert OPERATIONS_REPORT_GENERATED != OPERATIONS_REPORT_DEGRADED


def test_operations_diagnostic_is_a_plain_value_object() -> None:
    diagnostic = OperationsDiagnostic(category=OPERATIONS_REPORT_GENERATED, message="ok")

    assert diagnostic.category == OPERATIONS_REPORT_GENERATED
    assert diagnostic.message == "ok"
