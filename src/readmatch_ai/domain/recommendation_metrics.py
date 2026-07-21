from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationExecutionMetrics:
    """A deterministic, in-process snapshot of recommendation execution
    counters -- request/success/failure/fallback counts, total latency, and
    per-engine usage counts.

    Not a metrics-platform integration (no Prometheus/OpenTelemetry
    exporter) -- a plain, dependency-free value object suitable for
    deterministic testing and for one operator-facing summary (see the
    demo). `engine_usage_counts` is a plain Mapping, not a dict, so this
    remains genuinely immutable once produced.
    """

    request_count: int
    success_count: int
    failure_count: int
    fallback_count: int
    total_duration_seconds: float
    engine_usage_counts: Mapping[str, int]

    @property
    def average_duration_seconds(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_duration_seconds / self.request_count
