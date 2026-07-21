from __future__ import annotations

from readmatch_ai.domain.recommendation_execution import (
    RecommendationExecutionObserver,
    RecommendationExecutionRecord,
)
from readmatch_ai.domain.recommendation_metrics import RecommendationExecutionMetrics


class RecommendationMetricsCollector(RecommendationExecutionObserver):
    """Deterministic, in-process aggregator of RecommendationExecutionRecords.

    Implements RecommendationExecutionObserver so it can be notified
    directly (or fanned out to, alongside a logging observer, via
    CompositeRecommendationExecutionObserver) by
    infrastructure.observed_recommendation_engine after every recommend()
    call. Single-process, in-memory counters only -- not a metrics-platform
    client; `snapshot()` returns a plain, immutable
    RecommendationExecutionMetrics suitable for deterministic assertions.
    """

    def __init__(self) -> None:
        self._request_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._fallback_count = 0
        self._total_duration_seconds = 0.0
        self._engine_usage_counts: dict[str, int] = {}

    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        self._request_count += 1
        if record.success:
            self._success_count += 1
        else:
            self._failure_count += 1
        if record.used_fallback:
            self._fallback_count += 1
        self._total_duration_seconds += record.duration_seconds
        self._engine_usage_counts[record.engine_name] = (
            self._engine_usage_counts.get(record.engine_name, 0) + 1
        )

    def snapshot(self) -> RecommendationExecutionMetrics:
        return RecommendationExecutionMetrics(
            request_count=self._request_count,
            success_count=self._success_count,
            failure_count=self._failure_count,
            fallback_count=self._fallback_count,
            total_duration_seconds=self._total_duration_seconds,
            engine_usage_counts=dict(self._engine_usage_counts),
        )
