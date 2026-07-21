import pytest

from readmatch_ai.application.recommendation_metrics_collector import (
    RecommendationMetricsCollector,
)
from readmatch_ai.domain.recommendation_execution import (
    UNEXPECTED_FAILURE,
    RecommendationExecutionRecord,
)


def _record(**overrides: object) -> RecommendationExecutionRecord:
    defaults: dict[str, object] = {
        "request_id": "req-1",
        "engine_name": "popularity",
        "recommendation_type": "popularity",
        "duration_seconds": 0.1,
        "recommendation_count": 5,
        "used_fallback": False,
        "success": True,
        "error_classification": None,
    }
    defaults.update(overrides)
    return RecommendationExecutionRecord(**defaults)  # type: ignore[arg-type]


def test_snapshot_before_any_execution_is_all_zero() -> None:
    collector = RecommendationMetricsCollector()

    snapshot = collector.snapshot()

    assert snapshot.request_count == 0
    assert snapshot.success_count == 0
    assert snapshot.failure_count == 0
    assert snapshot.fallback_count == 0
    assert snapshot.total_duration_seconds == 0.0
    assert snapshot.engine_usage_counts == {}


def test_snapshot_aggregates_success_failure_fallback_and_duration() -> None:
    collector = RecommendationMetricsCollector()

    collector.on_execution(_record(success=True, duration_seconds=0.1))
    collector.on_execution(
        _record(success=False, error_classification=UNEXPECTED_FAILURE, duration_seconds=0.2)
    )
    collector.on_execution(_record(used_fallback=True, duration_seconds=0.3))

    snapshot = collector.snapshot()

    assert snapshot.request_count == 3
    assert snapshot.success_count == 2
    assert snapshot.failure_count == 1
    assert snapshot.fallback_count == 1
    assert snapshot.total_duration_seconds == pytest.approx(0.6)


def test_snapshot_counts_engine_usage_per_engine_name() -> None:
    collector = RecommendationMetricsCollector()

    collector.on_execution(_record(engine_name="popularity"))
    collector.on_execution(_record(engine_name="popularity"))
    collector.on_execution(_record(engine_name="hybrid"))

    snapshot = collector.snapshot()

    assert snapshot.engine_usage_counts == {"popularity": 2, "hybrid": 1}


def test_snapshot_is_deterministic_for_the_same_sequence_of_records() -> None:
    collector = RecommendationMetricsCollector()
    records = [_record(engine_name="popularity"), _record(engine_name="hybrid", success=False)]
    for record in records:
        collector.on_execution(record)

    first = collector.snapshot()
    second = collector.snapshot()

    assert first == second


def test_snapshot_is_a_point_in_time_copy_not_a_live_view() -> None:
    collector = RecommendationMetricsCollector()
    collector.on_execution(_record())

    snapshot = collector.snapshot()
    collector.on_execution(_record())

    assert snapshot.request_count == 1
    assert collector.snapshot().request_count == 2
