from __future__ import annotations

import os
from dataclasses import dataclass

_RUNTIME_MODE_ENV_VAR = "APPLICATION_MODE"

DEVELOPMENT_MODE = "development"
TEST_MODE = "test"
PRODUCTION_MODE = "production"
_VALID_RUNTIME_MODES = {DEVELOPMENT_MODE, TEST_MODE, PRODUCTION_MODE}


class UnknownRuntimeModeError(Exception):
    """Raised when APPLICATION_MODE is set to an unsupported value."""


def _resolve_runtime_mode() -> str:
    mode = os.environ.get(_RUNTIME_MODE_ENV_VAR, DEVELOPMENT_MODE)
    if mode not in _VALID_RUNTIME_MODES:
        raise UnknownRuntimeModeError(
            f"Unknown {_RUNTIME_MODE_ENV_VAR}: {mode!r} "
            f"(expected one of {sorted(_VALID_RUNTIME_MODES)})"
        )
    return mode


_BACKEND_ENV_VAR = "BOOK_REPOSITORY_BACKEND"
_DATABASE_URL_ENV_VAR = "DATABASE_URL"

IN_MEMORY_BACKEND = "in_memory"
POSTGRESQL_BACKEND = "postgresql"
_VALID_BACKENDS = {IN_MEMORY_BACKEND, POSTGRESQL_BACKEND}


class UnknownBookRepositoryBackendError(Exception):
    """Raised when BOOK_REPOSITORY_BACKEND is set to an unsupported value."""


class DatabaseUrlMissingError(Exception):
    """Raised when the postgresql backend is selected but DATABASE_URL is not set."""


@dataclass(frozen=True)
class BookRepositoryConfig:
    """Configuration selecting which BookRepository backend ApplicationContext composes."""

    backend: str
    database_url: str | None = None

    @classmethod
    def from_env(cls) -> BookRepositoryConfig:
        backend = os.environ.get(_BACKEND_ENV_VAR, IN_MEMORY_BACKEND)
        if backend not in _VALID_BACKENDS:
            raise UnknownBookRepositoryBackendError(
                f"Unknown {_BACKEND_ENV_VAR}: {backend!r} "
                f"(expected one of {sorted(_VALID_BACKENDS)})"
            )

        database_url = os.environ.get(_DATABASE_URL_ENV_VAR)
        if backend == POSTGRESQL_BACKEND and not database_url:
            raise DatabaseUrlMissingError(
                f"{_DATABASE_URL_ENV_VAR} must be set when "
                f"{_BACKEND_ENV_VAR}={POSTGRESQL_BACKEND!r}"
            )

        return cls(backend=backend, database_url=database_url)


_EMBEDDING_GENERATOR_BACKEND_ENV_VAR = "EMBEDDING_GENERATOR_BACKEND"
_EMBEDDING_MODEL_NAME_ENV_VAR = "EMBEDDING_MODEL_NAME"

DETERMINISTIC_BACKEND = "deterministic"
SENTENCE_TRANSFORMERS_BACKEND = "sentence_transformers"
_VALID_EMBEDDING_GENERATOR_BACKENDS = {DETERMINISTIC_BACKEND, SENTENCE_TRANSFORMERS_BACKEND}


class UnknownEmbeddingGeneratorBackendError(Exception):
    """Raised when EMBEDDING_GENERATOR_BACKEND is set to an unsupported value."""


@dataclass(frozen=True)
class EmbeddingGeneratorConfig:
    """Configuration selecting which BookEmbeddingGenerator ApplicationContext composes.

    Defaults to `deterministic` (DeterministicFakeBookEmbeddingGenerator) —
    unlike BookRepositoryConfig, this default is not meant to change for
    production use without an explicit opt-in, since the real provider is a
    heavy optional dependency.
    """

    backend: str
    model_name: str | None = None

    @classmethod
    def from_env(cls) -> EmbeddingGeneratorConfig:
        backend = os.environ.get(_EMBEDDING_GENERATOR_BACKEND_ENV_VAR, DETERMINISTIC_BACKEND)
        if backend not in _VALID_EMBEDDING_GENERATOR_BACKENDS:
            raise UnknownEmbeddingGeneratorBackendError(
                f"Unknown {_EMBEDDING_GENERATOR_BACKEND_ENV_VAR}: {backend!r} "
                f"(expected one of {sorted(_VALID_EMBEDDING_GENERATOR_BACKENDS)})"
            )

        model_name = os.environ.get(_EMBEDDING_MODEL_NAME_ENV_VAR)
        return cls(backend=backend, model_name=model_name)


_ALS_MODEL_PATH_ENV_VAR = "ALS_MODEL_PATH"


@dataclass(frozen=True)
class AlsModelConfig:
    """Configuration selecting where ApplicationContext persists/loads the trained ALS model.

    When `model_path` is set and a model already exists there, it's loaded
    instead of retraining. When unset (the default), a fresh model is
    trained in-process from the current UserBookInteractionRepository state
    every time — fine for tests/small fixtures, but a real deployment should
    set this so training happens once, not on every process start.
    """

    model_path: str | None = None

    @classmethod
    def from_env(cls) -> AlsModelConfig:
        return cls(model_path=os.environ.get(_ALS_MODEL_PATH_ENV_VAR))


_HYBRID_RANKING_STRATEGY_ENV_VAR = "HYBRID_RANKING_STRATEGY"

WEIGHTED_STRATEGY = "weighted"
RRF_STRATEGY = "rrf"
_VALID_RANKING_STRATEGIES = {WEIGHTED_STRATEGY, RRF_STRATEGY}


class UnknownRankingStrategyError(Exception):
    """Raised when HYBRID_RANKING_STRATEGY is set to an unsupported value."""


@dataclass(frozen=True)
class HybridRankingConfig:
    """Configuration selecting which RankingStrategy HybridRecommendationEngine composes with.

    Defaults to `weighted` (WeightedScoreFusionStrategy), matching the
    engine's original (Sprint 20) behavior.
    """

    strategy: str

    @classmethod
    def from_env(cls) -> HybridRankingConfig:
        strategy = os.environ.get(_HYBRID_RANKING_STRATEGY_ENV_VAR, WEIGHTED_STRATEGY)
        if strategy not in _VALID_RANKING_STRATEGIES:
            raise UnknownRankingStrategyError(
                f"Unknown {_HYBRID_RANKING_STRATEGY_ENV_VAR}: {strategy!r} "
                f"(expected one of {sorted(_VALID_RANKING_STRATEGIES)})"
            )
        return cls(strategy=strategy)


_CORS_ALLOWED_ORIGINS_ENV_VAR = "CORS_ALLOWED_ORIGINS"

# The Sprint 40 frontend's default local dev origin (`next dev` on port 3000).
_DEFAULT_CORS_ALLOWED_ORIGINS: tuple[str, ...] = ("http://localhost:3000",)


@dataclass(frozen=True)
class CorsConfig:
    """Configuration for which browser origins the API accepts cross-origin requests from.

    Purely a transport-layer concern (unlike BookRepositoryConfig/etc.): an
    unrecognised value can't leave the application in a broken state, so
    this never raises and isn't part of ApplicationConfiguration's
    startup-validation aggregation.
    """

    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> CorsConfig:
        raw = os.environ.get(_CORS_ALLOWED_ORIGINS_ENV_VAR)
        if raw is None:
            return cls(allowed_origins=_DEFAULT_CORS_ALLOWED_ORIGINS)
        origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
        return cls(allowed_origins=origins)


@dataclass(frozen=True)
class ConfigurationViolation:
    """One independent, operator-facing configuration problem.

    `code` is a stable, machine-checkable category (e.g.
    "unknown_book_repository_backend"); `field` names the affected
    environment variable/capability; `message` is a concise, human-readable
    explanation. Never carries a secret value -- every producer of this type
    (see ApplicationConfiguration.from_env and
    runtime_configuration.ApplicationConfigurationValidator) is responsible
    for that, mirroring the same discipline ReadinessCheckService already
    applies to ComponentCheck.detail (Sprint 31).
    """

    code: str
    field: str
    message: str


@dataclass(frozen=True)
class ApplicationConfiguration:
    """The application settings ApplicationContext.create() actually composes,
    aggregated from the existing per-capability config classes above plus the
    new runtime mode -- extending, not duplicating, the existing
    configuration mechanisms.

    Unlike BookRepositoryConfig.from_env()/etc. (each of which raises
    immediately on its own first invalid value), `from_env()` here resolves
    every category independently: an invalid value in one category never
    prevents detecting problems in another, so
    runtime_configuration.ApplicationConfigurationValidator can report every
    independent violation from one startup attempt. A category that failed
    to parse is `None` here; the corresponding `ConfigurationViolation` (same
    exception type/message the existing XConfig.from_env() would have
    raised) is in `parsing_violations`. `als_model` has no invalid values to
    reject (AlsModelConfig.from_env() never raises), so it's always present.
    """

    mode: str | None
    book_repository: BookRepositoryConfig | None
    embedding_generator: EmbeddingGeneratorConfig | None
    hybrid_ranking: HybridRankingConfig | None
    als_model: AlsModelConfig
    parsing_violations: tuple[ConfigurationViolation, ...]

    @classmethod
    def from_env(cls) -> ApplicationConfiguration:
        violations: list[ConfigurationViolation] = []

        mode: str | None
        try:
            mode = _resolve_runtime_mode()
        except UnknownRuntimeModeError as exc:
            violations.append(
                ConfigurationViolation(
                    code="unknown_runtime_mode", field=_RUNTIME_MODE_ENV_VAR, message=str(exc)
                )
            )
            mode = None

        book_repository: BookRepositoryConfig | None
        try:
            book_repository = BookRepositoryConfig.from_env()
        except UnknownBookRepositoryBackendError as exc:
            violations.append(
                ConfigurationViolation(
                    code="unknown_book_repository_backend", field=_BACKEND_ENV_VAR, message=str(exc)
                )
            )
            book_repository = None
        except DatabaseUrlMissingError as exc:
            violations.append(
                ConfigurationViolation(
                    code="database_url_missing", field=_DATABASE_URL_ENV_VAR, message=str(exc)
                )
            )
            book_repository = None

        embedding_generator: EmbeddingGeneratorConfig | None
        try:
            embedding_generator = EmbeddingGeneratorConfig.from_env()
        except UnknownEmbeddingGeneratorBackendError as exc:
            violations.append(
                ConfigurationViolation(
                    code="unknown_embedding_generator_backend",
                    field=_EMBEDDING_GENERATOR_BACKEND_ENV_VAR,
                    message=str(exc),
                )
            )
            embedding_generator = None

        hybrid_ranking: HybridRankingConfig | None
        try:
            hybrid_ranking = HybridRankingConfig.from_env()
        except UnknownRankingStrategyError as exc:
            violations.append(
                ConfigurationViolation(
                    code="unknown_hybrid_ranking_strategy",
                    field=_HYBRID_RANKING_STRATEGY_ENV_VAR,
                    message=str(exc),
                )
            )
            hybrid_ranking = None

        return cls(
            mode=mode,
            book_repository=book_repository,
            embedding_generator=embedding_generator,
            hybrid_ranking=hybrid_ranking,
            als_model=AlsModelConfig.from_env(),
            parsing_violations=tuple(violations),
        )
