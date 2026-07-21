#!/usr/bin/env python3
"""Validates the active runtime configuration (read from environment
variables) and prints a safe, redacted summary -- without starting the
application, building any repository/engine, or attempting any
Infrastructure connection.

Contains no validation logic of its own -- that all lives in
ApplicationConfiguration (readmatch_ai.config) and
ApplicationConfigurationValidator (readmatch_ai.runtime_configuration), the
exact same rules ApplicationContext.create() applies via
RuntimeBootstrapValidator at real application startup. This script exists so
an operator can check configuration validity (e.g. before `uvicorn
readmatch_ai.api.main:app` or `docker compose up`) without paying the cost --
or side effects -- of actually composing the application.

Usage:
    python scripts/validate_runtime.py
"""

from __future__ import annotations

import sys

from readmatch_ai.config import ApplicationConfiguration
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

    if result.valid:
        print("Configuration valid.")
        print(
            "\nNote: this confirms structural/operational prerequisites only -- it does not "
            "guarantee every external dependency (e.g. the database) will remain reachable "
            "after startup; see GET /readiness for a live dependency probe."
        )
        return 0

    print(f"Configuration invalid -- {len(result.violations)} violation(s):\n")
    for violation in result.violations:
        print(f"  [{violation.code}] {violation.field}: {violation.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
