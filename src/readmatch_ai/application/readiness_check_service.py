from __future__ import annotations

from readmatch_ai.config import ApplicationConfiguration
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.health import ComponentCheck, ReadinessStatus
from readmatch_ai.domain.persistence_validation import PersistenceRuntimeValidator
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.runtime_configuration import ApplicationConfigurationValidator


class ReadinessCheckService:
    """Readiness: are this instance's required runtime dependencies
    currently available to serve requests.

    Distinct from HealthCheckService: a process can be healthy (alive,
    correctly composed) while not ready (its database connection just
    dropped, or required configuration has become invalid). Takes the
    already-resolved `book_repository`/`recommendation_engines` directly
    (Domain ports), the same way every other Application use case depends
    on ports rather than the ApplicationContext composition root itself --
    depending on ApplicationContext here would invert that dependency
    direction and create a circular import (ApplicationContext.create()
    is what constructs this service).

    `persistence_runtime_validator` (Sprint 33) is optional and defaults to
    `None` -- every existing caller (and every Fake/In-memory-backed test)
    keeps working unchanged. When provided (ApplicationContext wires one
    only for a genuinely PostgreSQL-backed repository), `check()` adds one
    additional `persistence_runtime` ComponentCheck; when `None`, that
    check is omitted entirely (never reported as trivially available),
    since there is nothing to validate for an in-memory repository.
    """

    def __init__(
        self,
        book_repository: BookRepository,
        recommendation_engines: dict[str, RecommendationEngine],
        persistence_runtime_validator: PersistenceRuntimeValidator | None = None,
    ) -> None:
        self._book_repository = book_repository
        self._recommendation_engines = recommendation_engines
        self._persistence_runtime_validator = persistence_runtime_validator

    def check(self) -> ReadinessStatus:
        checks = [
            self._check_configuration(),
            self._check_book_repository(),
            self._check_recommendation_composition(),
        ]
        validator = self._persistence_runtime_validator
        if validator is not None:
            checks.append(self._check_persistence_runtime(validator))
        return ReadinessStatus(
            ready=all(check.available for check in checks), checks=tuple(checks)
        )

    def _check_configuration(self) -> ComponentCheck:
        # Re-parses the same env-derived configuration
        # ApplicationContext.create() already validated at startup (Sprint
        # 32's ApplicationConfiguration/ApplicationConfigurationValidator --
        # extended here, not duplicated) -- redundant in the common case,
        # but a real, deterministic, side-effect-free signal if runtime
        # configuration has become invalid since then (e.g. an operator
        # changed an env var without restarting). Violation messages never
        # carry a secret value (see ConfigurationViolation's own docstring),
        # so joining them into `detail` is safe.
        configuration = ApplicationConfiguration.from_env()
        result = ApplicationConfigurationValidator().validate(configuration)
        if not result.valid:
            detail = "; ".join(f"{v.field}: {v.message}" for v in result.violations)
            return ComponentCheck(name="configuration", available=False, detail=detail)
        return ComponentCheck(name="configuration", available=True)

    def _check_book_repository(self) -> ComponentCheck:
        # A read-only lookup of a random, essentially-never-present id --
        # exercises real repository connectivity (e.g. an actual query
        # against PostgreSQL) without depending on any specific book
        # existing. Broad `except Exception` is deliberate here: this
        # check's entire purpose is to catch whatever infrastructure
        # failure the concrete adapter might raise (a connection error, a
        # timeout, ...) without this service needing to import any
        # PostgreSQL-specific exception type. Only the exception's class
        # name is surfaced, never str(exc), since driver error messages can
        # embed connection details.
        try:
            self._book_repository.get_by_id(BookId.generate())
        except Exception as exc:
            return ComponentCheck(
                name="book_repository",
                available=False,
                detail=f"{type(exc).__name__} while checking repository availability",
            )
        return ComponentCheck(name="book_repository", available=True)

    def _check_recommendation_composition(self) -> ComponentCheck:
        # Structural, not functional: confirms every named recommendation
        # engine was actually supplied. Given Python's type system this is
        # necessarily coarse (a caller can't easily construct this service
        # with a missing engine at all), but it's still a real, named,
        # documented signal -- not a live smoke-test of each engine's own
        # recommend() (which could have side effects or introduce
        # latency/nondeterminism into a readiness probe).
        missing = [name for name, engine in self._recommendation_engines.items() if engine is None]
        return ComponentCheck(
            name="recommendation_composition",
            available=not missing,
            detail=f"missing engines: {', '.join(missing)}" if missing else None,
        )

    def _check_persistence_runtime(
        self, validator: PersistenceRuntimeValidator
    ) -> ComponentCheck:
        # Delegates entirely to the injected validator (Sprint 33) --
        # PostgreSQL connectivity, required schema/pgvector
        # extension/dimension/index -- this service never touches psycopg
        # itself. Violation messages are already safe (see
        # PersistenceValidationViolation's own docstring), so joining them
        # into `detail` carries no secret.
        result = validator.validate()
        if result.valid:
            return ComponentCheck(name="persistence_runtime", available=True)
        detail = "; ".join(f"{v.component}: {v.message}" for v in result.violations)
        return ComponentCheck(name="persistence_runtime", available=False, detail=detail)
