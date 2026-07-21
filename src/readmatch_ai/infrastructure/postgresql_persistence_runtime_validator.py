from __future__ import annotations

import logging
import re

import psycopg

from readmatch_ai.domain.persistence_validation import (
    PersistenceRuntimeValidator,
    PersistenceValidationResult,
    PersistenceValidationViolation,
)

_LOGGER_NAME = "readmatch_ai.persistence"

_REQUIRED_TABLES = ("books", "book_popularity", "book_embeddings", "user_book_interactions")
_VECTOR_TABLE = "book_embeddings"
_VECTOR_COLUMN = "vector"
_VECTOR_INDEX = "idx_book_embeddings_vector_cosine"

# 384 matches every currently-wired BookEmbeddingGenerator's output width --
# DeterministicFakeBookEmbeddingGenerator's default, and
# sentence-transformers/all-MiniLM-L6-v2's actual output size -- and
# migrations/0005_widen_book_embeddings_vector_to_384.sql's fixed pgvector
# column width. Restates an existing, documented system invariant; not a
# speculative new rule.
_DEFAULT_EXPECTED_VECTOR_DIMENSIONS = 384

_VECTOR_TYPE_PATTERN = re.compile(r"^vector\((\d+)\)$")


class PostgreSQLPersistenceRuntimeValidator(PersistenceRuntimeValidator):
    """Read-only validation of a live PostgreSQL + pgvector runtime.

    Takes an already-open psycopg.Connection -- lifecycle owned by the
    caller. ApplicationContext._compose() reuses the same connection
    already open for PostgreSQLBookRepository (a live, long-lived
    connection kept for the app's lifetime, mirroring how
    ReadinessCheckService's existing book_repository check already reuses
    that same connection rather than opening a new one per readiness
    call); validate_postgresql_persistence() below instead opens and
    closes its own short-lived connection, for callers (the CLI) with no
    existing one. Every check is a plain read-only SELECT against
    pg_catalog/information_schema -- never a write, never a schema change
    (no CREATE/ALTER/migration is ever run here).
    """

    def __init__(
        self,
        connection: psycopg.Connection,
        expected_vector_dimensions: int = _DEFAULT_EXPECTED_VECTOR_DIMENSIONS,
    ) -> None:
        self._connection = connection
        self._expected_vector_dimensions = expected_vector_dimensions

    def validate(self) -> PersistenceValidationResult:
        violations: list[PersistenceValidationViolation] = []
        checked: list[str] = []

        violations.extend(self._check_connectivity())
        checked.append("connectivity")

        missing_tables, table_violations = self._check_required_tables()
        violations.extend(table_violations)
        checked.append("required_tables")

        violations.extend(self._check_pgvector_extension())
        checked.append("pgvector_extension")

        if _VECTOR_TABLE not in missing_tables:
            violations.extend(self._check_vector_dimension())
            checked.append("vector_dimension")

            violations.extend(self._check_vector_index())
            checked.append("vector_index")

        result = PersistenceValidationResult(
            violations=tuple(violations), checked_components=tuple(checked)
        )
        _log_persistence_diagnostic(result)
        return result

    def _check_connectivity(self) -> list[PersistenceValidationViolation]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except psycopg.Error as exc:
            return [
                PersistenceValidationViolation(
                    code="postgresql_unreachable",
                    component="connectivity",
                    message=f"{type(exc).__name__} while checking PostgreSQL connectivity",
                )
            ]
        return []

    def _check_required_tables(
        self,
    ) -> tuple[set[str], list[PersistenceValidationViolation]]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = ANY(%s)",
                    (list(_REQUIRED_TABLES),),
                )
                present = {row[0] for row in cursor.fetchall()}
        except psycopg.Error as exc:
            return set(), [
                PersistenceValidationViolation(
                    code="schema_inspection_failed",
                    component="required_tables",
                    message=f"{type(exc).__name__} while inspecting required tables",
                )
            ]
        missing = set(_REQUIRED_TABLES) - present
        violations = [
            PersistenceValidationViolation(
                code="missing_required_table",
                component=table,
                message=f"Required table {table!r} was not found",
            )
            for table in sorted(missing)
        ]
        return missing, violations

    def _check_pgvector_extension(self) -> list[PersistenceValidationViolation]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                found = cursor.fetchone() is not None
        except psycopg.Error as exc:
            return [
                PersistenceValidationViolation(
                    code="schema_inspection_failed",
                    component="pgvector_extension",
                    message=f"{type(exc).__name__} while checking the pgvector extension",
                )
            ]
        if found:
            return []
        return [
            PersistenceValidationViolation(
                code="pgvector_extension_missing",
                component="pgvector_extension",
                message="The pgvector 'vector' extension is not installed",
            )
        ]

    def _check_vector_dimension(self) -> list[PersistenceValidationViolation]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "SELECT format_type(a.atttypid, a.atttypmod) "
                    "FROM pg_attribute a JOIN pg_class c ON a.attrelid = c.oid "
                    "WHERE c.relname = %s AND a.attname = %s",
                    (_VECTOR_TABLE, _VECTOR_COLUMN),
                )
                row = cursor.fetchone()
        except psycopg.Error as exc:
            return [
                PersistenceValidationViolation(
                    code="schema_inspection_failed",
                    component="vector_dimension",
                    message=f"{type(exc).__name__} while checking the vector column type",
                )
            ]
        if row is None:
            return [
                PersistenceValidationViolation(
                    code="vector_column_missing",
                    component="vector_dimension",
                    message=f"Column {_VECTOR_TABLE}.{_VECTOR_COLUMN} was not found",
                )
            ]
        match = _VECTOR_TYPE_PATTERN.match(row[0])
        if match is None:
            return [
                PersistenceValidationViolation(
                    code="vector_column_not_a_vector_type",
                    component="vector_dimension",
                    message=f"{_VECTOR_TABLE}.{_VECTOR_COLUMN} is not a pgvector column",
                )
            ]
        actual_dimensions = int(match.group(1))
        if actual_dimensions == self._expected_vector_dimensions:
            return []
        return [
            PersistenceValidationViolation(
                code="vector_dimension_mismatch",
                component="vector_dimension",
                message=(
                    f"{_VECTOR_TABLE}.{_VECTOR_COLUMN} is vector({actual_dimensions}), "
                    f"expected vector({self._expected_vector_dimensions})"
                ),
            )
        ]

    def _check_vector_index(self) -> list[PersistenceValidationViolation]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
                    "AND tablename = %s AND indexname = %s",
                    (_VECTOR_TABLE, _VECTOR_INDEX),
                )
                found = cursor.fetchone() is not None
        except psycopg.Error as exc:
            return [
                PersistenceValidationViolation(
                    code="schema_inspection_failed",
                    component="vector_index",
                    message=f"{type(exc).__name__} while checking the required vector index",
                )
            ]
        if found:
            return []
        return [
            PersistenceValidationViolation(
                code="missing_required_index",
                component="vector_index",
                message=f"Required index {_VECTOR_INDEX!r} was not found on {_VECTOR_TABLE}",
            )
        ]


def _log_persistence_diagnostic(result: PersistenceValidationResult) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    level = logging.INFO if result.valid else logging.ERROR
    logger.log(
        level,
        "persistence_validation valid=%s checked=%s violation_count=%d",
        result.valid,
        ",".join(result.checked_components),
        len(result.violations),
    )


def validate_postgresql_persistence(database_url: str) -> PersistenceValidationResult:
    """Convenience entry point for a caller with no already-open connection
    (see scripts/validate_runtime.py) -- opens a short-lived connection,
    validates, and always closes it afterward.

    A connection failure itself becomes one PersistenceValidationViolation
    (never a raised exception, never str(exc), which could embed
    connection details) rather than crashing the caller.
    """
    try:
        connection = psycopg.connect(database_url)
    except psycopg.Error as exc:
        return PersistenceValidationResult(
            violations=(
                PersistenceValidationViolation(
                    code="postgresql_unreachable",
                    component="connectivity",
                    message=f"{type(exc).__name__} while connecting to PostgreSQL",
                ),
            ),
            checked_components=("connectivity",),
        )
    try:
        return PostgreSQLPersistenceRuntimeValidator(connection).validate()
    finally:
        connection.close()
