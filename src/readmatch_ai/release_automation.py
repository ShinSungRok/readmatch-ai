from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.config import POSTGRESQL_BACKEND, ApplicationConfiguration
from readmatch_ai.deployment_validation import ContainerRuntimeValidator
from readmatch_ai.infrastructure.postgresql_persistence_runtime_validator import (
    validate_postgresql_persistence,
)
from readmatch_ai.operations import OperationsService
from readmatch_ai.runtime_configuration import (
    ApplicationConfigurationValidator,
    RuntimeConfigurationSummary,
)

_LOGGER_NAME = "readmatch_ai.release"

_TestCommand = tuple[str, tuple[str, ...]]

_DEFAULT_TEST_COMMANDS: tuple[_TestCommand, ...] = (
    ("ruff", ("ruff", "check", "src", "tests", "scripts")),
    ("mypy", ("mypy", "src", "tests", "scripts")),
    ("pytest", ("pytest", "-q")),
)
_TEST_COMMAND_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class ReleaseValidationViolation:
    """One independent, safe-to-log release validation problem.

    `stage` names which pipeline stage found it (configuration/persistence/
    deployment/operations/tests); `message` never includes a secret value --
    every producer of this type translates from an already-redacted
    upstream violation (ConfigurationViolation, PersistenceValidationViolation,
    DeploymentValidationViolation), or names a subprocess/exit code only.
    """

    code: str
    stage: str
    message: str


@dataclass(frozen=True)
class ReleaseValidationResult:
    """The outcome of one ReleaseAutomationService.validate() run.

    `checked_stages` names every stage this run actually reached, in
    order -- persistence/deployment/operations/tests are all skipped
    (never even attempted) once configuration itself is known invalid,
    since none of them could succeed against an invalid environment and
    each would otherwise report a confusing, redundant secondary failure
    for the same root cause.
    """

    violations: tuple[ReleaseValidationViolation, ...]
    checked_stages: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.violations


RELEASE_VALIDATION_SUCCEEDED = "release_validation_succeeded"
RELEASE_VALIDATION_FAILURE = "release_validation_failure"


@dataclass(frozen=True)
class ReleaseDiagnostic:
    """One structured, loggable release-validation-run outcome.

    Reuses the Sprint 31-35 structured-logging boundary (stdlib `logging`,
    one message per event, a `readmatch_ai.*`-namespaced logger) rather
    than introducing a second, unrelated operational-event system.
    """

    category: str
    message: str


def log_release_diagnostic(diagnostic: ReleaseDiagnostic) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    level = (
        logging.INFO if diagnostic.category == RELEASE_VALIDATION_SUCCEEDED else logging.ERROR
    )
    logger.log(
        level, "release_validation category=%s message=%s", diagnostic.category, diagnostic.message
    )


@dataclass(frozen=True)
class ReleaseSummary:
    """A flat, safe, operator-facing at-a-glance view of one
    ReleaseValidationResult -- deterministic, no secrets (mode and
    application_version are the only configuration values included,
    already redacted by RuntimeConfigurationSummary).
    """

    valid: bool
    mode: str | None
    checked_stages: tuple[str, ...]
    violation_count: int
    application_version: str

    @classmethod
    def build(cls, result: ReleaseValidationResult) -> ReleaseSummary:
        configuration = ApplicationConfiguration.from_env()
        validation = ApplicationConfigurationValidator().validate(configuration)
        configuration_summary = RuntimeConfigurationSummary.build(configuration, validation)
        return cls(
            valid=result.valid,
            mode=configuration_summary.mode,
            checked_stages=result.checked_stages,
            violation_count=len(result.violations),
            application_version=configuration_summary.application_version,
        )


class ReleaseAutomationService:
    """Deterministic release validation pipeline -- orchestrates, never
    reimplements, every existing validation capability:

    1. **configuration** (Sprint 32) -- ApplicationConfiguration.from_env()
       + ApplicationConfigurationValidator. If invalid, every later stage
       is skipped entirely (never even attempted) -- no PostgreSQL
       connection, deployment simulation, or ApplicationContext build is
       ever performed against an already-known-invalid environment,
       mirroring the same "no infrastructure attempt after static
       validation failure" discipline established in Sprint 32/33.
    2. **persistence** (Sprint 33) -- only when the configured backend is
       `postgresql`; skipped (not just vacuously passed) otherwise, via
       `validate_postgresql_persistence`.
    3. **deployment** (Sprint 34) -- `ContainerRuntimeValidator`, exercising
       the real application entrypoint end-to-end.
    4. **operations** (Sprint 35) -- builds one `ApplicationContext` and
       generates an `OperationsReport`; a non-operational report becomes
       one coarse violation here (the report's own health/readiness
       detail already explains *why*, via `scripts/operations_report.py`).
    5. **tests** (optional, `include_tests=True`, off by default since it
       is comparatively slow) -- runs the project's own quality gates
       (`ruff check`, `mypy --strict`, `pytest -q`) as subprocesses, each
       failure becoming one violation naming the failing command and exit
       code (never raw stdout/stderr, which could be large or leak
       environment detail).

    `context_factory`/`deployment_validator`/`test_commands` are all
    injectable (preserving dependency injection), defaulting to the real
    production paths, so tests can exercise every stage -- including a
    non-operational operations stage, and both passing and failing test
    commands -- deterministically, without needing a real broken
    environment or recursively re-running this project's own test suite.
    """

    def __init__(
        self,
        *,
        context_factory: Callable[[], ApplicationContext] | None = None,
        deployment_validator: ContainerRuntimeValidator | None = None,
        test_commands: Sequence[_TestCommand] | None = None,
    ) -> None:
        self._context_factory = context_factory or ApplicationContext.create
        self._deployment_validator = deployment_validator or ContainerRuntimeValidator()
        self._test_commands = tuple(
            test_commands if test_commands is not None else _DEFAULT_TEST_COMMANDS
        )

    def validate(self, *, include_tests: bool = False) -> ReleaseValidationResult:
        violations: list[ReleaseValidationViolation] = []
        checked: list[str] = ["configuration"]

        configuration = ApplicationConfiguration.from_env()
        configuration_result = ApplicationConfigurationValidator().validate(configuration)
        if not configuration_result.valid:
            violations.extend(
                ReleaseValidationViolation(code=v.code, stage="configuration", message=v.message)
                for v in configuration_result.violations
            )
            return self._finish(violations, checked)

        if (
            configuration.book_repository is not None
            and configuration.book_repository.backend == POSTGRESQL_BACKEND
        ):
            checked.append("persistence")
            assert configuration.book_repository.database_url is not None
            persistence_result = validate_postgresql_persistence(
                configuration.book_repository.database_url
            )
            violations.extend(
                ReleaseValidationViolation(code=v.code, stage="persistence", message=v.message)
                for v in persistence_result.violations
            )

        checked.append("deployment")
        deployment_result = self._deployment_validator.validate()
        violations.extend(
            ReleaseValidationViolation(code=v.code, stage="deployment", message=v.message)
            for v in deployment_result.violations
        )

        checked.append("operations")
        violations.extend(self._check_operations())

        if include_tests:
            checked.append("tests")
            violations.extend(self._run_test_commands())

        return self._finish(violations, checked)

    def _check_operations(self) -> list[ReleaseValidationViolation]:
        try:
            context = self._context_factory()
        except Exception as exc:
            return [
                ReleaseValidationViolation(
                    code="operations_context_build_failed",
                    stage="operations",
                    message=f"{type(exc).__name__} while building ApplicationContext",
                )
            ]
        operations_report = OperationsService(context).generate_report()
        if operations_report.operational:
            return []
        return [
            ReleaseValidationViolation(
                code="operations_report_not_operational",
                stage="operations",
                message="Operations report is not operational -- see health/readiness detail",
            )
        ]

    def _run_test_commands(self) -> list[ReleaseValidationViolation]:
        violations: list[ReleaseValidationViolation] = []
        for name, command in self._test_commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=_TEST_COMMAND_TIMEOUT_SECONDS,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                violations.append(
                    ReleaseValidationViolation(
                        code=f"{name}_command_failed",
                        stage="tests",
                        message=f"{type(exc).__name__} running {name!r}",
                    )
                )
                continue
            if result.returncode != 0:
                violations.append(
                    ReleaseValidationViolation(
                        code=f"{name}_failed",
                        stage="tests",
                        message=f"{name!r} exited with code {result.returncode}",
                    )
                )
        return violations

    @staticmethod
    def _finish(
        violations: list[ReleaseValidationViolation], checked: list[str]
    ) -> ReleaseValidationResult:
        result = ReleaseValidationResult(
            violations=tuple(violations), checked_stages=tuple(checked)
        )
        category = RELEASE_VALIDATION_SUCCEEDED if result.valid else RELEASE_VALIDATION_FAILURE
        log_release_diagnostic(
            ReleaseDiagnostic(category=category, message=f"{len(result.violations)} violation(s)")
        )
        return result
