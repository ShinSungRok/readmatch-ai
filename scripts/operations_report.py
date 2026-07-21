#!/usr/bin/env python3
"""Generates a deterministic, read-only operational status report --
aggregating health, readiness (already reflecting persistence integration,
Sprint 33), runtime configuration (Sprint 32), and recommendation execution
metrics (Sprint 31) from a real ApplicationContext, without reimplementing
any of those underlying checks.

Contains no operations business logic of its own -- that all lives in
OperationsService (readmatch_ai.operations), which only ever delegates to
the same health/readiness/configuration/metrics/deployment capabilities
every prior Sprint already built.

Usage:
    python scripts/operations_report.py
    python scripts/operations_report.py --include-deployment-check
"""

from __future__ import annotations

import argparse
import sys

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.operations import OperationsReport, OperationsService, RuntimeOperationsSummary


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        context = ApplicationContext.create()
    except Exception as exc:
        print(
            f"Could not build ApplicationContext: {type(exc).__name__} -- the application "
            "itself cannot start, so no operations report can be generated. Run "
            "scripts/validate_deployment.py (or scripts/validate_runtime.py) for full startup "
            "diagnostics."
        )
        return 1

    report = OperationsService(context).generate_report(
        include_deployment_check=args.include_deployment_check
    )
    summary = RuntimeOperationsSummary.build(report)

    print("Operations report:\n")
    print(f"  mode: {summary.mode}")
    print(f"  healthy: {summary.healthy}")
    print(f"  ready: {summary.ready}")
    print(f"  configuration_valid: {summary.configuration_valid}")
    if summary.deployment_valid is not None:
        print(f"  deployment_valid: {summary.deployment_valid}")
    print(f"  recommendation_requests: {summary.recommendation_request_count}")
    print(f"  recommendation_failures: {summary.recommendation_failure_count}")
    print(f"  application_version: {summary.application_version}")
    print()

    _print_failing_checks(report)

    if summary.operational:
        print("Operational.")
        return 0

    print("Not operational.")
    return 1


def _print_failing_checks(report: OperationsReport) -> None:
    if not report.health.healthy:
        print("Health issues:")
        for check in report.health.checks:
            if not check.available:
                print(f"  - {check.name}: {check.detail or 'unavailable'}")
        print()

    if not report.readiness.ready:
        print("Readiness issues:")
        for check in report.readiness.checks:
            if not check.available:
                print(f"  - {check.name}: {check.detail or 'unavailable'}")
        print()

    if report.deployment is not None and not report.deployment.valid:
        print("Deployment issues:")
        for violation in report.deployment.violations:
            print(f"  - [{violation.code}] {violation.component}: {violation.message}")
        print()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic, read-only operations report."
    )
    parser.add_argument(
        "--include-deployment-check",
        action="store_true",
        help=(
            "Also run the full deployment/startup validation (Sprint 34, "
            "builds a fresh ApplicationContext) -- slower, optional."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
