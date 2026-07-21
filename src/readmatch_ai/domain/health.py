from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentCheck:
    """One named, deterministic check performed by Health or Readiness.

    `detail` is an optional, human-readable explanation for an unavailable
    check -- never a raw exception message that might embed a database
    connection string or other infrastructure detail (see
    ReadinessCheckService, which is careful about what it puts here).
    """

    name: str
    available: bool
    detail: str | None = None


@dataclass(frozen=True)
class HealthStatus:
    """Whether the application process itself is operating normally.

    Distinct from ReadinessStatus: Health answers "is this process alive
    and internally intact", not "are this process's external dependencies
    currently reachable" -- a process can be healthy while not ready (e.g.
    its database connection just dropped), and the reverse is not
    meaningful (an unhealthy process can't usefully evaluate readiness).
    Transport-independent: no HTTP status code or response-model concept
    lives here.
    """

    healthy: bool
    checks: tuple[ComponentCheck, ...]


@dataclass(frozen=True)
class ReadinessStatus:
    """Whether this instance's required runtime dependencies are currently
    available to serve requests -- repositories, recommendation
    composition, and runtime configuration.

    Transport-independent, mirroring HealthStatus's shape exactly.
    """

    ready: bool
    checks: tuple[ComponentCheck, ...]
