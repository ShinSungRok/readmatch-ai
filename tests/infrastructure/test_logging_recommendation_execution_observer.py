import logging

import pytest

from readmatch_ai.domain.recommendation_execution import RecommendationExecutionRecord
from readmatch_ai.infrastructure.logging_recommendation_execution_observer import (
    LoggingRecommendationExecutionObserver,
)


def _record(**overrides: object) -> RecommendationExecutionRecord:
    defaults: dict[str, object] = {
        "request_id": "req-1",
        "engine_name": "popularity",
        "recommendation_type": "popularity",
        "duration_seconds": 0.01,
        "recommendation_count": 5,
        "used_fallback": False,
        "success": True,
        "error_classification": None,
    }
    defaults.update(overrides)
    return RecommendationExecutionRecord(**defaults)  # type: ignore[arg-type]


def test_successful_execution_logs_at_info_level(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test.readmatch_ai.recommendation_execution.success")
    observer = LoggingRecommendationExecutionObserver(logger=logger)

    with caplog.at_level(logging.INFO, logger=logger.name):
        observer.on_execution(_record(request_id="req-42", success=True))

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelno == logging.INFO
    message = log_record.getMessage()
    assert "req-42" in message
    assert "popularity" in message


def test_failed_execution_logs_at_warning_level(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test.readmatch_ai.recommendation_execution.failure")
    observer = LoggingRecommendationExecutionObserver(logger=logger)

    with caplog.at_level(logging.INFO, logger=logger.name):
        observer.on_execution(_record(success=False, error_classification="unexpected_failure"))

    log_record = caplog.records[0]
    assert log_record.levelno == logging.WARNING
    assert "unexpected_failure" in log_record.getMessage()


def test_default_logger_uses_the_recommendation_execution_namespace(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observer = LoggingRecommendationExecutionObserver()

    with caplog.at_level(logging.INFO, logger="readmatch_ai.recommendation_execution"):
        observer.on_execution(_record())

    assert len(caplog.records) == 1
    assert caplog.records[0].name == "readmatch_ai.recommendation_execution"
