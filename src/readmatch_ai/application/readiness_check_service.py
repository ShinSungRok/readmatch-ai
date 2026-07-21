from __future__ import annotations

from readmatch_ai.config import (
    BookRepositoryConfig,
    DatabaseUrlMissingError,
    EmbeddingGeneratorConfig,
    HybridRankingConfig,
    UnknownBookRepositoryBackendError,
    UnknownEmbeddingGeneratorBackendError,
    UnknownRankingStrategyError,
)
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_repository import BookRepository
from readmatch_ai.domain.health import ComponentCheck, ReadinessStatus
from readmatch_ai.domain.recommendation_engine import RecommendationEngine

_CONFIGURATION_ERRORS = (
    UnknownBookRepositoryBackendError,
    DatabaseUrlMissingError,
    UnknownEmbeddingGeneratorBackendError,
    UnknownRankingStrategyError,
)


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
    """

    def __init__(
        self,
        book_repository: BookRepository,
        recommendation_engines: dict[str, RecommendationEngine],
    ) -> None:
        self._book_repository = book_repository
        self._recommendation_engines = recommendation_engines

    def check(self) -> ReadinessStatus:
        checks = (
            self._check_configuration(),
            self._check_book_repository(),
            self._check_recommendation_composition(),
        )
        return ReadinessStatus(ready=all(check.available for check in checks), checks=checks)

    def _check_configuration(self) -> ComponentCheck:
        # Re-parses the same env-derived config ApplicationContext.create()
        # already resolved at startup -- redundant in the common case, but
        # a real, deterministic, side-effect-free signal if runtime
        # configuration has become invalid since then. Error messages from
        # these specific exceptions only ever name a backend/env-var, never
        # a secret value (see config.py), so `str(exc)` is safe to surface.
        try:
            BookRepositoryConfig.from_env()
            EmbeddingGeneratorConfig.from_env()
            HybridRankingConfig.from_env()
        except _CONFIGURATION_ERRORS as exc:
            return ComponentCheck(name="configuration", available=False, detail=str(exc))
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
