from __future__ import annotations

from readmatch_ai.domain.health import ComponentCheck, HealthStatus


class HealthCheckService:
    """Health: is the application process itself operating normally.

    Deliberately independent of external dependency reachability (that is
    ReadinessCheckService's job, which takes concrete Domain ports so it
    can actually probe them) -- a lightweight, side-effect-free self-check
    with no dependencies of its own. Answering an HTTP request at all
    already demonstrates the process is alive and its own composition
    succeeded at startup (had it failed, the process wouldn't be running to
    answer this check); deeper self-checks (e.g. deadlock detection) are a
    documented future enhancement, not implemented here.
    """

    def check(self) -> HealthStatus:
        checks = (ComponentCheck(name="process", available=True),)
        return HealthStatus(healthy=all(check.available for check in checks), checks=checks)
