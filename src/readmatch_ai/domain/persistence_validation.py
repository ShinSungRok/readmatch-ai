from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceValidationViolation:
    """One independent, read-only-discoverable problem with the production
    persistence runtime.

    Distinct from config.ConfigurationViolation (Sprint 32): this reflects
    a live runtime dependency fact -- PostgreSQL unreachable, a required
    table/extension/index missing, an incompatible vector dimension -- not
    a static environment-variable parsing problem. Never carries a secret
    value: `message` never includes a DATABASE_URL, credential, vector, or
    user data.
    """

    code: str
    component: str
    message: str


@dataclass(frozen=True)
class PersistenceValidationResult:
    """The outcome of one PersistenceRuntimeValidator.validate() call.

    `checked_components` names every component this run actually
    inspected, in order -- some checks (vector dimension, the vector
    index) are skipped when a prerequisite (the book_embeddings table
    itself) is already known missing, to avoid a confusing cascade of
    secondary errors for the same root cause.
    """

    violations: tuple[PersistenceValidationViolation, ...]
    checked_components: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.violations


class PersistenceRuntimeValidator(ABC):
    """Port for read-only validation of the production persistence runtime
    -- PostgreSQL connectivity, required schema, and pgvector
    extension/dimension/index.

    Implemented by
    infrastructure.postgresql_persistence_runtime_validator.PostgreSQLPersistenceRuntimeValidator;
    consumed by ReadinessCheckService without that Application service ever
    depending on psycopg. Never performs a write or schema change --
    validation only.
    """

    @abstractmethod
    def validate(self) -> PersistenceValidationResult:
        """Run every read-only persistence check and return the aggregated result."""


@dataclass(frozen=True)
class PersistenceRuntimeSummary:
    """A safe, redacted, operator-facing snapshot of persistence runtime
    validation -- deterministic, no secrets, no vectors, no user data.

    `applicable=False` (an in-memory repository, or no PostgreSQL-backed
    repository was actually composed) means there is nothing to validate;
    `valid` is trivially True in that case, mirroring how
    ReadinessCheckService simply omits its persistence_runtime check
    entirely when validation doesn't apply.
    """

    applicable: bool
    valid: bool
    checked_components: tuple[str, ...]
    violation_count: int

    @classmethod
    def build(cls, result: PersistenceValidationResult | None) -> PersistenceRuntimeSummary:
        if result is None:
            return cls(applicable=False, valid=True, checked_components=(), violation_count=0)
        return cls(
            applicable=True,
            valid=result.valid,
            checked_components=result.checked_components,
            violation_count=len(result.violations),
        )
