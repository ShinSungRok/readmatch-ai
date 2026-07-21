from __future__ import annotations

import logging
from dataclasses import dataclass

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.deployment_validation import ContainerRuntimeValidator, DeploymentValidationResult
from readmatch_ai.domain.health import HealthStatus, ReadinessStatus
from readmatch_ai.domain.recommendation_metrics import RecommendationExecutionMetrics
from readmatch_ai.runtime_configuration import RuntimeConfigurationSummary

_LOGGER_NAME = "readmatch_ai.operations"


@dataclass(frozen=True)
class OperationsReport:
    """One deterministic, read-only, safe operational snapshot -- aggregating
    the already-existing health, readiness, runtime configuration, and
    recommendation-metrics capabilities (Sprints 31-33) without
    reimplementing any of their checks.

    `readiness` already reflects persistence integration through its own
    `persistence_runtime` check (Sprint 33) when applicable -- satisfying
    "persistence inspection" purely through reuse, with no separate
    persistence field here. `deployment` is `None` unless explicitly
    requested (see OperationsService.generate_report), since re-running a
    full startup simulation (a fresh ApplicationContext.create() call,
    Sprint 34) is neither necessary nor free -- an already-running context
    generating this report is itself evidence the application already
    started successfully.
    """

    health: HealthStatus
    readiness: ReadinessStatus
    configuration: RuntimeConfigurationSummary
    recommendation_metrics: RecommendationExecutionMetrics
    deployment: DeploymentValidationResult | None = None

    @property
    def operational(self) -> bool:
        base = (
            self.health.healthy
            and self.readiness.ready
            and self.configuration.configuration_valid
        )
        if self.deployment is not None:
            return base and self.deployment.valid
        return base


@dataclass(frozen=True)
class RuntimeOperationsSummary:
    """A flat, safe, operator-facing at-a-glance view of one OperationsReport
    -- deterministic, no secrets (every constituent value already redacted
    by its own Sprint 31/32/33/34 producer).
    """

    operational: bool
    mode: str | None
    healthy: bool
    ready: bool
    configuration_valid: bool
    deployment_valid: bool | None
    recommendation_request_count: int
    recommendation_failure_count: int
    application_version: str

    @classmethod
    def build(cls, report: OperationsReport) -> RuntimeOperationsSummary:
        return cls(
            operational=report.operational,
            mode=report.configuration.mode,
            healthy=report.health.healthy,
            ready=report.readiness.ready,
            configuration_valid=report.configuration.configuration_valid,
            deployment_valid=report.deployment.valid if report.deployment is not None else None,
            recommendation_request_count=report.recommendation_metrics.request_count,
            recommendation_failure_count=report.recommendation_metrics.failure_count,
            application_version=report.configuration.application_version,
        )


OPERATIONS_REPORT_GENERATED = "operations_report_generated"
OPERATIONS_REPORT_DEGRADED = "operations_report_degraded"


@dataclass(frozen=True)
class OperationsDiagnostic:
    """One structured, loggable operations-report-generation outcome.

    Reuses the Sprint 31/32/33/34 structured-logging boundary (stdlib
    `logging`, one message per event, a `readmatch_ai.*`-namespaced logger)
    rather than introducing a second, unrelated operational-event system.
    """

    category: str
    message: str


def log_operations_diagnostic(diagnostic: OperationsDiagnostic) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    level = (
        logging.INFO if diagnostic.category == OPERATIONS_REPORT_GENERATED else logging.WARNING
    )
    logger.log(
        level, "operations_report category=%s message=%s", diagnostic.category, diagnostic.message
    )


class OperationsService:
    """Deterministic, read-only aggregation of the platform's existing
    runtime capabilities into one OperationsReport -- runtime inspection
    (configuration), deployment inspection (optional, Sprint 34), health
    inspection, readiness inspection (already reflecting persistence
    integration), and observability inspection (recommendation metrics).

    Takes an already-constructed ApplicationContext directly (unlike
    HealthCheckService/ReadinessCheckService, which deliberately avoid
    depending on ApplicationContext to prevent a circular import with
    ApplicationContext.create() itself, since those two ARE fields
    ApplicationContext.create() constructs). OperationsService is
    intentionally never added as an ApplicationContext field -- it
    operates on an already-fully-composed context from outside, exactly
    like Sprint 34's ContainerRuntimeValidator, so no such cycle exists
    here.

    Performs no destructive action -- every underlying check it delegates
    to is already read-only by construction.
    """

    def __init__(self, application_context: ApplicationContext) -> None:
        self._context = application_context

    def generate_report(self, *, include_deployment_check: bool = False) -> OperationsReport:
        deployment = ContainerRuntimeValidator().validate() if include_deployment_check else None
        report = OperationsReport(
            health=self._context.health_check_service.check(),
            readiness=self._context.readiness_check_service.check(),
            configuration=self._context.runtime_configuration_summary,
            recommendation_metrics=self._context.recommendation_metrics_collector.snapshot(),
            deployment=deployment,
        )
        category = (
            OPERATIONS_REPORT_GENERATED if report.operational else OPERATIONS_REPORT_DEGRADED
        )
        log_operations_diagnostic(
            OperationsDiagnostic(category=category, message=f"operational={report.operational}")
        )
        return report
