from __future__ import annotations

import logging

from readmatch_ai.domain.recommendation_execution import (
    RecommendationExecutionObserver,
    RecommendationExecutionRecord,
)

_DEFAULT_LOGGER_NAME = "readmatch_ai.recommendation_execution"


class LoggingRecommendationExecutionObserver(RecommendationExecutionObserver):
    """Logs each RecommendationExecutionRecord as one structured message via
    the Python standard library's `logging` module -- no external logging
    framework or monitoring platform.

    Successful executions log at INFO (silent by default under Python's
    standard root-logger configuration, so demo/test output stays clean
    unless a handler/level is explicitly configured); failures log at
    WARNING (visible by default). This adapter only ever logs the fields
    already on RecommendationExecutionRecord, which itself excludes
    embedding vectors, latent factors, raw interaction history, secrets,
    and connection information by construction -- there is nothing else
    here for this adapter to accidentally leak.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(_DEFAULT_LOGGER_NAME)

    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        level = logging.INFO if record.success else logging.WARNING
        self._logger.log(
            level,
            "recommendation_execution request_id=%s engine=%s type=%s duration_s=%.4f "
            "count=%d fallback=%s success=%s error=%s",
            record.request_id,
            record.engine_name,
            record.recommendation_type,
            record.duration_seconds,
            record.recommendation_count,
            record.used_fallback,
            record.success,
            record.error_classification,
        )
