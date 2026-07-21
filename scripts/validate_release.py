#!/usr/bin/env python3
"""Runs the full, deterministic release validation pipeline -- orchestrating,
not reimplementing, every existing validation capability: runtime
configuration (Sprint 32), persistence (Sprint 33, when the configured
backend is postgresql), deployment (Sprint 34), and an operations report
(Sprint 35). A statically invalid configuration short-circuits every later
stage -- no PostgreSQL connection, deployment simulation, or
ApplicationContext build is ever attempted against an already-known-invalid
environment.

Optionally (`--include-tests`) also runs this project's own quality gates
(`ruff check`, `mypy --strict`, `pytest -q`) as subprocesses -- the same
commands `.github/workflows/ci.yml` already runs, invoked here for a single
local pre-release check. Off by default since it is comparatively slow.

Contains no validation logic of its own -- that all lives in
ReleaseAutomationService (readmatch_ai.release_automation), which only ever
delegates to the same configuration/persistence/deployment/operations
capabilities every prior Sprint already built.

Usage:
    python scripts/validate_release.py
    python scripts/validate_release.py --include-tests
"""

from __future__ import annotations

import argparse
import sys

from readmatch_ai.release_automation import ReleaseAutomationService, ReleaseSummary


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    result = ReleaseAutomationService().validate(include_tests=args.include_tests)
    summary = ReleaseSummary.build(result)

    print("Release validation summary:\n")
    print(f"  mode: {summary.mode}")
    print(f"  checked: {', '.join(summary.checked_stages)}")
    print(f"  valid: {summary.valid}")
    print(f"  application_version: {summary.application_version}")
    print()

    if result.valid:
        print("Release valid.")
        return 0

    print(f"Release invalid -- {len(result.violations)} violation(s):\n")
    for violation in result.violations:
        print(f"  [{violation.code}] {violation.stage}: {violation.message}")
    return 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deterministic release validation pipeline."
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Also run ruff check / mypy --strict / pytest -q as subprocesses -- slower, optional.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
