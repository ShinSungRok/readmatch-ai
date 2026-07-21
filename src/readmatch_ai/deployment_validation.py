from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from readmatch_ai.api.main import create_app
from readmatch_ai.config import ApplicationConfiguration
from readmatch_ai.runtime_configuration import RuntimeBootstrapFailure

_LOGGER_NAME = "readmatch_ai.deployment"


@dataclass(frozen=True)
class DeploymentValidationViolation:
    """One independent, safe-to-log deployment validation problem.

    `message` never includes a secret value -- see the discipline already
    established by config.ConfigurationViolation (Sprint 32) and
    domain.persistence_validation.PersistenceValidationViolation (Sprint
    33), which this module follows exactly.
    """

    code: str
    component: str
    message: str


@dataclass(frozen=True)
class DeploymentValidationResult:
    """The outcome of one ContainerRuntimeValidator.validate() call.

    `checked_components` names every component this run actually
    inspected, in order -- `health`/`readiness`/`api` are only appended
    (and only checked at all) when `startup` itself succeeded, since none
    of those endpoints exist to check against an application that never
    finished starting.
    """

    violations: tuple[DeploymentValidationViolation, ...]
    checked_components: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.violations


DEPLOYMENT_VALIDATION_FAILURE = "deployment_validation_failure"
DEPLOYMENT_VALIDATION_SUCCEEDED = "deployment_validation_succeeded"


@dataclass(frozen=True)
class DeploymentDiagnostic:
    """One structured, loggable deployment-validation-run outcome.

    Reuses the Sprint 31/32/33 structured-logging boundary (stdlib
    `logging`, one message per event, a `readmatch_ai.*`-namespaced
    logger) rather than introducing a second, unrelated operational-event
    system.
    """

    category: str
    message: str
    violations: tuple[DeploymentValidationViolation, ...] = ()


def log_deployment_diagnostic(diagnostic: DeploymentDiagnostic) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    level = (
        logging.INFO if diagnostic.category == DEPLOYMENT_VALIDATION_SUCCEEDED else logging.ERROR
    )
    logger.log(
        level,
        "deployment_validation category=%s message=%s violation_count=%d",
        diagnostic.category,
        diagnostic.message,
        len(diagnostic.violations),
    )


@dataclass(frozen=True)
class RuntimeEnvironmentSummary:
    """A safe, redacted, operator-facing snapshot of one deployment
    validation run -- deterministic, no secrets.

    `mode` is computed independently from the current environment (never
    from a possibly-never-built ApplicationContext), so it's always
    available even when startup itself failed -- the one useful thing an
    operator can still learn about *why* in that case.
    """

    mode: str | None
    valid: bool
    checked_components: tuple[str, ...]
    violation_count: int

    @classmethod
    def build(cls, result: DeploymentValidationResult) -> RuntimeEnvironmentSummary:
        configuration = ApplicationConfiguration.from_env()
        return cls(
            mode=configuration.mode,
            valid=result.valid,
            checked_components=result.checked_components,
            violation_count=len(result.violations),
        )


class ContainerRuntimeValidator:
    """Deterministic, end-to-end validation of the application's own
    deployment/container startup sequence.

    Reuses, never duplicates: `api.main.create_app()`/
    `ApplicationContext.create()` -- the exact same production entrypoint
    the Dockerfile's `uvicorn readmatch_ai.api.main:app` CMD serves,
    including RuntimeBootstrapValidator's fail-fast configuration
    validation (Sprint 32) -- for startup verification, and the existing
    `GET /health`/`GET /readiness` endpoints (Sprint 31, extended in
    Sprint 33 to reflect persistence integration) for health/readiness
    verification. `GET /recommendations/popularity` is checked as a
    minimal, real proof of API availability beyond the observability
    endpoints themselves.

    Driven via FastAPI's TestClient (`raise_server_exceptions=False`, so a
    handler-level failure becomes an ordinary 500 response to check,
    rather than propagating into this validator) -- deterministic, no
    real network, running container, or production credentials required,
    exactly how every existing API test in this codebase already
    validates the application. Never writes to a database; every
    exercised endpoint is already read-only by construction.

    `app_factory` defaults to the real `create_app` and is injectable
    (preserving dependency injection) so tests can validate against a
    deliberately-broken ApplicationContext without needing real
    infrastructure.
    """

    def __init__(self, app_factory: Callable[[], FastAPI] | None = None) -> None:
        self._app_factory = app_factory or create_app

    def validate(self) -> DeploymentValidationResult:
        violations: list[DeploymentValidationViolation] = []
        checked: list[str] = ["startup"]

        try:
            with TestClient(self._app_factory(), raise_server_exceptions=False) as client:
                checked.append("health")
                violations.extend(
                    self._check_json(client.get("/health"), component="health", valid_key="healthy")
                )
                checked.append("readiness")
                violations.extend(
                    self._check_json(
                        client.get("/readiness"), component="readiness", valid_key="ready"
                    )
                )
                checked.append("api")
                violations.extend(
                    self._check_status(client.get("/recommendations/popularity"), component="api")
                )
        except RuntimeBootstrapFailure as exc:
            violations.append(
                DeploymentValidationViolation(
                    code="startup_configuration_invalid",
                    component="startup",
                    message=f"{len(exc.result.violations)} configuration violation(s) found",
                )
            )
        except Exception as exc:
            violations.append(
                DeploymentValidationViolation(
                    code="startup_failed",
                    component="startup",
                    message=f"{type(exc).__name__} during application startup",
                )
            )

        result = DeploymentValidationResult(
            violations=tuple(violations), checked_components=tuple(checked)
        )
        log_deployment_diagnostic(
            DeploymentDiagnostic(
                category=(
                    DEPLOYMENT_VALIDATION_SUCCEEDED
                    if result.valid
                    else DEPLOYMENT_VALIDATION_FAILURE
                ),
                message=f"{len(result.violations)} violation(s) found",
                violations=result.violations,
            )
        )
        return result

    @staticmethod
    def _check_json(
        response: Any, *, component: str, valid_key: str
    ) -> list[DeploymentValidationViolation]:
        try:
            body = response.json()
        except ValueError:
            return [
                DeploymentValidationViolation(
                    code=f"{component}_endpoint_malformed_response",
                    component=component,
                    message=(
                        f"GET /{component} returned a non-JSON response "
                        f"(HTTP {response.status_code})"
                    ),
                )
            ]
        if response.status_code == 200 and body.get(valid_key) is True:
            return []
        failing = [
            check["name"] for check in body.get("checks", []) if not check.get("available", True)
        ]
        detail = f" (failing: {', '.join(failing)})" if failing else ""
        return [
            DeploymentValidationViolation(
                code=f"{component}_endpoint_unhealthy",
                component=component,
                message=f"GET /{component} returned HTTP {response.status_code}{detail}",
            )
        ]

    @staticmethod
    def _check_status(response: Any, *, component: str) -> list[DeploymentValidationViolation]:
        if response.status_code == 200:
            return []
        return [
            DeploymentValidationViolation(
                code=f"{component}_endpoint_unavailable",
                component=component,
                message=(
                    f"GET /recommendations/popularity returned HTTP {response.status_code}"
                ),
            )
        ]
