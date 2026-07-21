from readmatch_ai.domain.recommendation_execution import (
    UNEXPECTED_FAILURE,
    VALIDATION_FAILURE,
    CompositeRecommendationExecutionObserver,
    RecommendationExecutionObserver,
    RecommendationExecutionRecord,
)


class _RecordingObserver(RecommendationExecutionObserver):
    def __init__(self) -> None:
        self.received: list[RecommendationExecutionRecord] = []

    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        self.received.append(record)


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


def test_record_defaults_error_classification_to_none() -> None:
    record = _record()

    assert record.error_classification is None


def test_validation_and_unexpected_failure_are_distinct_classifications() -> None:
    assert VALIDATION_FAILURE != UNEXPECTED_FAILURE


def test_composite_observer_fans_out_to_every_observer() -> None:
    first = _RecordingObserver()
    second = _RecordingObserver()
    composite = CompositeRecommendationExecutionObserver([first, second])
    record = _record()

    composite.on_execution(record)

    assert first.received == [record]
    assert second.received == [record]


def test_composite_observer_with_no_observers_does_nothing() -> None:
    composite = CompositeRecommendationExecutionObserver([])

    composite.on_execution(_record())
