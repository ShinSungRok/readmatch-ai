from __future__ import annotations

import os
from dataclasses import dataclass

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
