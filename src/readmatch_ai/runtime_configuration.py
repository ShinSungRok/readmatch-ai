from __future__ import annotations

import logging
from dataclasses import dataclass

from readmatch_ai import __version__
from readmatch_ai.config import (
    IN_MEMORY_BACKEND,
    PRODUCTION_MODE,
    ApplicationConfiguration,
    ConfigurationViolation,
)

_STARTUP_LOGGER_NAME = "readmatch_ai.startup"

_TEST_ONLY_BOOK_REPOSITORY_BACKENDS = frozenset({IN_MEMORY_BACKEND})
_VALID_DATABASE_URL_SCHEMES = ("postgresql://", "postgres://")


@dataclass(frozen=True)
class ConfigurationValidationResult:
    """The outcome of validating one ApplicationConfiguration.

    `violations` aggregates every independent problem found -- both
    parsing-time violations already carried on the configuration (an
    unknown backend, a missing DATABASE_URL, ...) and the additional
    cross-field/business-rule violations this module's own
    ApplicationConfigurationValidator adds -- so an operator sees every
    correctable problem from one run, not just the first.
    """

    violations: tuple[ConfigurationViolation, ...]

    @property
    def valid(self) -> bool:
        return not self.violations


class ApplicationConfigurationValidator:
    """Deterministic, side-effect-free business-rule validation over an
    already-parsed ApplicationConfiguration.

    Layered on top of ApplicationConfiguration.from_env()'s own
    parsing_violations (missing/unknown values per category) with rules
    that only make sense once more than one category is known together:
    production mode must not silently run on a non-persistent (test-only)
    repository backend, and a configured DATABASE_URL must at least use a
    valid PostgreSQL URL scheme. Performs no I/O of its own -- no
    connection is ever attempted here, only string/field inspection --
    consistent with "no infrastructure attempt after static validation
    failure."
    """

    def validate(self, configuration: ApplicationConfiguration) -> ConfigurationValidationResult:
        violations = list(configuration.parsing_violations)
        violations.extend(self._check_production_persistence(configuration))
        violations.extend(self._check_database_url_form(configuration))
        return ConfigurationValidationResult(violations=tuple(violations))

    def _check_production_persistence(
        self, configuration: ApplicationConfiguration
    ) -> list[ConfigurationViolation]:
        if configuration.mode != PRODUCTION_MODE or configuration.book_repository is None:
            return []
        if configuration.book_repository.backend not in _TEST_ONLY_BOOK_REPOSITORY_BACKENDS:
            return []
        return [
            ConfigurationViolation(
                code="production_mode_requires_persistent_repository",
                field="BOOK_REPOSITORY_BACKEND",
                message=(
                    f"APPLICATION_MODE={PRODUCTION_MODE!r} requires a persistent "
                    f"BOOK_REPOSITORY_BACKEND; got {configuration.book_repository.backend!r}, "
                    "a test-only, non-persistent adapter"
                ),
            )
        ]

    def _check_database_url_form(
        self, configuration: ApplicationConfiguration
    ) -> list[ConfigurationViolation]:
        book_repository = configuration.book_repository
        if book_repository is None or book_repository.database_url is None:
            return []
        if book_repository.database_url.startswith(_VALID_DATABASE_URL_SCHEMES):
            return []
        return [
            ConfigurationViolation(
                code="invalid_database_url_form",
                field="DATABASE_URL",
                message=(
                    f"DATABASE_URL must start with one of {_VALID_DATABASE_URL_SCHEMES} "
                    "(the value itself is never included in this message)"
                ),
            )
        ]


@dataclass(frozen=True)
class RuntimeConfigurationSummary:
    """A safe, redacted, operator-facing snapshot of the active runtime
    configuration -- deterministic field order, no secrets.

    Explicitly excludes DATABASE_URL (and any other secret/connection
    value): only the adapter *category* each capability resolved to is
    included (e.g. "postgresql", not the URL itself), mirroring the same
    redaction discipline ReadinessCheckService already applies (Sprint 31).
    A category that failed to parse is represented as `None`, the same
    convention ApplicationConfiguration.from_env() itself uses.
    """

    mode: str | None
    book_repository_backend: str | None
    embedding_generator_backend: str | None
    embedding_model_name: str | None
    hybrid_ranking_strategy: str | None
    observability_enabled: bool
    configuration_valid: bool
    application_version: str

    @classmethod
    def build(
        cls, configuration: ApplicationConfiguration, validation: ConfigurationValidationResult
    ) -> RuntimeConfigurationSummary:
        return cls(
            mode=configuration.mode,
            book_repository_backend=(
                configuration.book_repository.backend
                if configuration.book_repository is not None
                else None
            ),
            embedding_generator_backend=(
                configuration.embedding_generator.backend
                if configuration.embedding_generator is not None
                else None
            ),
            embedding_model_name=(
                configuration.embedding_generator.model_name
                if configuration.embedding_generator is not None
                else None
            ),
            hybrid_ranking_strategy=(
                configuration.hybrid_ranking.strategy
                if configuration.hybrid_ranking is not None
                else None
            ),
            observability_enabled=True,
            configuration_valid=validation.valid,
            application_version=__version__,
        )


CONFIGURATION_VALIDATION_FAILURE = "configuration_validation_failure"
COMPOSITION_FAILURE = "composition_failure"
STARTUP_SUCCEEDED = "startup_succeeded"


@dataclass(frozen=True)
class StartupDiagnostic:
    """One structured, loggable startup-phase outcome.

    `category` is a fixed vocabulary distinguishing why (or whether)
    startup failed -- configuration_validation_failure (static, before any
    Infrastructure connection was attempted) vs. composition_failure
    (raised while actually building repositories/engines, e.g. a real
    database connection failure) vs. startup_succeeded. Reuses the Sprint
    31 structured-logging boundary (stdlib `logging`, one message per
    event, a `readmatch_ai.*`-namespaced logger) rather than introducing a
    second, unrelated operational-event system.
    """

    category: str
    message: str
    violations: tuple[ConfigurationViolation, ...] = ()


def log_startup_diagnostic(diagnostic: StartupDiagnostic) -> None:
    logger = logging.getLogger(_STARTUP_LOGGER_NAME)
    level = logging.INFO if diagnostic.category == STARTUP_SUCCEEDED else logging.ERROR
    logger.log(
        level,
        "startup category=%s message=%s violation_count=%d",
        diagnostic.category,
        diagnostic.message,
        len(diagnostic.violations),
    )


class RuntimeBootstrapFailure(Exception):
    """Raised by RuntimeBootstrapValidator.require_valid() when static
    configuration validation fails.

    Carries the full ConfigurationValidationResult so callers
    (ApplicationContext.create(), scripts/validate_runtime.py) can report
    every aggregated violation, not just the first.
    """

    def __init__(self, result: ConfigurationValidationResult) -> None:
        self.result = result
        summary = "; ".join(f"[{v.code}] {v.field}: {v.message}" for v in result.violations)
        super().__init__(f"Invalid runtime configuration: {summary}")


class RuntimeBootstrapValidator:
    """The single integration point for fail-fast startup validation --
    called by both ApplicationContext.create() and
    scripts/validate_runtime.py, so validation rules are never duplicated
    between the real application boot path and the operator-facing CLI.

    Performs only static, deterministic checks (env parsing plus
    ApplicationConfigurationValidator's business rules) -- no repository,
    embedding, or other Infrastructure connection is ever attempted here,
    satisfying "infrastructure connections are not attempted when
    configuration is already invalid."
    """

    def __init__(self, validator: ApplicationConfigurationValidator | None = None) -> None:
        self._validator = validator or ApplicationConfigurationValidator()

    def validate(
        self, configuration: ApplicationConfiguration | None = None
    ) -> ConfigurationValidationResult:
        resolved = (
            configuration if configuration is not None else ApplicationConfiguration.from_env()
        )
        return self._validator.validate(resolved)

    def require_valid(
        self, configuration: ApplicationConfiguration | None = None
    ) -> ApplicationConfiguration:
        resolved = (
            configuration if configuration is not None else ApplicationConfiguration.from_env()
        )
        result = self._validator.validate(resolved)
        if not result.valid:
            log_startup_diagnostic(
                StartupDiagnostic(
                    category=CONFIGURATION_VALIDATION_FAILURE,
                    message=f"{len(result.violations)} configuration violation(s) found",
                    violations=result.violations,
                )
            )
            raise RuntimeBootstrapFailure(result)
        return resolved
