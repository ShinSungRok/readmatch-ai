#!/usr/bin/env python3
"""Validates the active runtime configuration (read from environment
variables) and, when a PostgreSQL backend is selected and statically valid,
the live persistence runtime (connectivity, required schema, pgvector
extension/dimension/index) -- printing a safe, redacted summary throughout.
Never starts the application or builds a full ApplicationContext, and never
attempts any connection -- to PostgreSQL or otherwise -- while static
configuration is already invalid.

Contains no validation logic of its own -- static configuration rules live
in ApplicationConfiguration (readmatch_ai.config) and
ApplicationConfigurationValidator (readmatch_ai.runtime_configuration, the
exact same rules ApplicationContext.create() applies via
RuntimeBootstrapValidator at real startup); persistence runtime rules live
in PostgreSQLPersistenceRuntimeValidator
(readmatch_ai.infrastructure.postgresql_persistence_runtime_validator, the
same validator ReadinessCheckService's persistence_runtime check reuses).
This script exists so an operator can check both before `uvicorn
readmatch_ai.api.main:app` or `docker compose up`, without paying the cost
-- or side effects -- of actually composing the application.

Usage:
    python scripts/validate_runtime.py
"""

from __future__ import annotations

import sys

from readmatch_ai.config import POSTGRESQL_BACKEND, ApplicationConfiguration
from readmatch_ai.domain.persistence_validation import PersistenceRuntimeSummary
from readmatch_ai.infrastructure.postgresql_persistence_runtime_validator import (
    validate_postgresql_persistence,
)
from readmatch_ai.runtime_configuration import (
    ApplicationConfigurationValidator,
    RuntimeConfigurationSummary,
)


def main(argv: list[str] | None = None) -> int:
    del argv  # No arguments: this command only reads the current environment.

    configuration = ApplicationConfiguration.from_env()
    result = ApplicationConfigurationValidator().validate(configuration)
    summary = RuntimeConfigurationSummary.build(configuration, result)

    print("Runtime configuration summary:\n")
    print(f"  mode: {summary.mode}")
    print(f"  book_repository_backend: {summary.book_repository_backend}")
    print(f"  embedding_generator_backend: {summary.embedding_generator_backend}")
    print(f"  embedding_model_name: {summary.embedding_model_name}")
    print(f"  hybrid_ranking_strategy: {summary.hybrid_ranking_strategy}")
    print(f"  observability_enabled: {summary.observability_enabled}")
    print(f"  application_version: {summary.application_version}")
    print()

    if not result.valid:
        print(f"Configuration invalid -- {len(result.violations)} violation(s):\n")
        for violation in result.violations:
            print(f"  [{violation.code}] {violation.field}: {violation.message}")
        print(
            "\nSkipping persistence runtime validation -- static configuration must be valid "
            "first (no PostgreSQL connection is attempted otherwise)."
        )
        return 1

    print("Configuration valid.")

    persistence_valid = True
    if (
        configuration.book_repository is not None
        and configuration.book_repository.backend == POSTGRESQL_BACKEND
    ):
        assert configuration.book_repository.database_url is not None
        persistence_result = validate_postgresql_persistence(
            configuration.book_repository.database_url
        )
        persistence_summary = PersistenceRuntimeSummary.build(persistence_result)
        persistence_valid = persistence_summary.valid

        print("\nPersistence runtime summary:\n")
        print(f"  checked: {', '.join(persistence_summary.checked_components)}")
        print(f"  valid: {persistence_summary.valid}")
        if not persistence_result.valid:
            print(
                f"\nPersistence runtime invalid -- {len(persistence_result.violations)} "
                "violation(s):\n"
            )
            for persistence_violation in persistence_result.violations:
                print(
                    f"  [{persistence_violation.code}] {persistence_violation.component}: "
                    f"{persistence_violation.message}"
                )
    else:
        print(
            "\nPersistence runtime validation not applicable "
            "(book_repository_backend is not postgresql)."
        )

    print(
        "\nNote: this confirms structural/operational prerequisites only -- it does not "
        "guarantee every external dependency (e.g. the database) will remain reachable "
        "after startup; see GET /readiness for a live dependency probe."
    )
    return 0 if persistence_valid else 1


if __name__ == "__main__":
    sys.exit(main())
