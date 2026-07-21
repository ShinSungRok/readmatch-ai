from readmatch_ai.domain.recommendation_metrics import RecommendationExecutionMetrics


def test_average_duration_seconds_divides_total_by_request_count() -> None:
    metrics = RecommendationExecutionMetrics(
        request_count=4,
        success_count=4,
        failure_count=0,
        fallback_count=0,
        total_duration_seconds=2.0,
        engine_usage_counts={},
    )

    assert metrics.average_duration_seconds == 0.5


def test_average_duration_seconds_is_zero_when_no_requests() -> None:
    metrics = RecommendationExecutionMetrics(
        request_count=0,
        success_count=0,
        failure_count=0,
        fallback_count=0,
        total_duration_seconds=0.0,
        engine_usage_counts={},
    )

    assert metrics.average_duration_seconds == 0.0
