from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

VALIDATION_FAILURE = "validation_failure"
UNEXPECTED_FAILURE = "unexpected_failure"


@dataclass(frozen=True)
class RecommendationExecutionRecord:
    """A structured, transport/logging-library-independent record of one
    completed recommendation request.

    This is the entire observability payload for a request -- what a
    RecommendationExecutionObserver receives, and what a concrete logging
    adapter (Infrastructure) serializes. Deliberately excludes everything
    on this Sprint's "do not log" list: no embedding vectors, ALS latent
    factors, raw interaction history, secrets, API keys, or database
    connection information -- only identifiers, counts, and timing.

    `used_fallback` is defined narrowly and observably: true when the
    request carried neither a source book nor a user (so whatever the
    engine returned could only have come from the baseline/non-personalized
    signal) -- a coarse, honest, purely query-derived signal, not a claim
    about which internal engine/policy branch actually ran (see
    infrastructure.observed_recommendation_engine).
    """

    request_id: str
    engine_name: str
    recommendation_type: str
    duration_seconds: float
    recommendation_count: int
    used_fallback: bool
    success: bool
    error_classification: str | None = None


class RecommendationExecutionObserver(ABC):
    """Port for reacting to one completed recommendation execution.

    Concrete implementations include a metrics aggregator
    (application.recommendation_metrics_collector.RecommendationMetricsCollector)
    and a structured-logging adapter
    (infrastructure.logging_recommendation_execution_observer); both share
    this one contract so infrastructure.observed_recommendation_engine has
    exactly one thing to notify per request.
    """

    @abstractmethod
    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        """React to one completed recommendation execution."""


class CompositeRecommendationExecutionObserver(RecommendationExecutionObserver):
    """Fans one execution record out to multiple observers.

    Lets the Composition Root notify e.g. both a metrics collector and a
    logging adapter from a single observer reference, without either
    observer knowing the other exists.
    """

    def __init__(self, observers: Sequence[RecommendationExecutionObserver]) -> None:
        self._observers = list(observers)

    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        for observer in self._observers:
            observer.on_execution(record)
