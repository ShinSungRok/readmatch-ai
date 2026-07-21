#!/usr/bin/env python3
"""Validates that the application starts successfully and that GET /health,
GET /readiness, and a real recommendation endpoint are all reachable and
healthy -- driving the exact same FastAPI app object
(readmatch_ai.api.main:create_app()) the Dockerfile's own
`uvicorn readmatch_ai.api.main:app` entrypoint serves, via an in-process
TestClient. Deterministic; requires no real running container, network
access, or production credentials.

Contains no validation logic of its own -- that all lives in
ContainerRuntimeValidator (readmatch_ai.deployment_validation), which in
turn reuses RuntimeBootstrapValidator (Sprint 32) for startup/configuration
validation and the existing GET /health / GET /readiness endpoints (Sprint
31, extended in Sprint 33 to reflect persistence integration) rather than
reimplementing any of it.

Usage:
    python scripts/validate_deployment.py
"""

from __future__ import annotations

import sys

from readmatch_ai.deployment_validation import ContainerRuntimeValidator, RuntimeEnvironmentSummary


def main(argv: list[str] | None = None) -> int:
    del argv  # No arguments: this command only validates the local application.

    result = ContainerRuntimeValidator().validate()
    summary = RuntimeEnvironmentSummary.build(result)

    print("Deployment validation summary:\n")
    print(f"  mode: {summary.mode}")
    print(f"  checked: {', '.join(summary.checked_components)}")
    print(f"  valid: {summary.valid}")
    print()

    if result.valid:
        print(
            "Deployment valid -- the application starts successfully and "
            "GET /health, GET /readiness, and a real recommendation endpoint are all reachable."
        )
        return 0

    print(f"Deployment invalid -- {len(result.violations)} violation(s):\n")
    for violation in result.violations:
        print(f"  [{violation.code}] {violation.component}: {violation.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
