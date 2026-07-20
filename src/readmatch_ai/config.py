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
