import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.recommendation_execution import (
    UNEXPECTED_FAILURE,
    VALIDATION_FAILURE,
    RecommendationExecutionObserver,
    RecommendationExecutionRecord,
)
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.observed_recommendation_engine import ObservedRecommendationEngine


class _RecordingObserver(RecommendationExecutionObserver):
    def __init__(self) -> None:
        self.received: list[RecommendationExecutionRecord] = []

    def on_execution(self, record: RecommendationExecutionRecord) -> None:
        self.received.append(record)


class _StubEngine(RecommendationEngine):
    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        return RecommendationResult(recommendation=Recommendation(items=self._items))


class _RaisingEngine(RecommendationEngine):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        raise self._exc


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Title"),
        author=Author("Author"),
        category=Category("Category"),
    )


def _item() -> RecommendationItem:
    return RecommendationItem(book=_book(), score=1.0, source="fake")


def _clock_sequence(values: list[float]) -> object:
    iterator = iter(values)

    def clock() -> float:
        return next(iterator)

    return clock


def test_successful_execution_reports_recommendation_count_and_success() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([_item(), _item()]),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
    )

    engine.recommend(RecommendationQuery(limit=2))

    assert len(observer.received) == 1
    record = observer.received[0]
    assert record.engine_name == "popularity"
    assert record.recommendation_type == "popularity"
    assert record.recommendation_count == 2
    assert record.success is True
    assert record.error_classification is None


def test_duration_is_recorded_from_the_injected_clock() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([]),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
        clock=_clock_sequence([10.0, 10.25]),  # type: ignore[arg-type]
    )

    engine.recommend(RecommendationQuery(limit=1))

    assert observer.received[0].duration_seconds == pytest.approx(0.25)


def test_request_id_comes_from_the_injected_factory() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([]),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
        request_id_factory=lambda: "fixed-request-id",
    )

    engine.recommend(RecommendationQuery(limit=1))

    assert observer.received[0].request_id == "fixed-request-id"


def test_used_fallback_is_true_when_query_has_no_book_id_and_no_user_id() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([]), observer, engine_name="popularity", recommendation_type="popularity"
    )

    engine.recommend(RecommendationQuery(limit=1))

    assert observer.received[0].used_fallback is True


def test_used_fallback_is_false_when_query_has_a_user_id() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([]), observer, engine_name="reranked", recommendation_type="personalized"
    )

    engine.recommend(RecommendationQuery(limit=1, user_id=UserId.generate()))

    assert observer.received[0].used_fallback is False


def test_value_error_is_classified_as_validation_failure_and_reraised() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _RaisingEngine(ValueError("bad input")),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
    )

    with pytest.raises(ValueError, match="bad input"):
        engine.recommend(RecommendationQuery(limit=1))

    record = observer.received[0]
    assert record.success is False
    assert record.error_classification == VALIDATION_FAILURE
    assert record.recommendation_count == 0


def test_unexpected_exception_is_classified_as_unexpected_failure_and_reraised() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _RaisingEngine(RuntimeError("boom")),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
    )

    with pytest.raises(RuntimeError, match="boom"):
        engine.recommend(RecommendationQuery(limit=1))

    record = observer.received[0]
    assert record.success is False
    assert record.error_classification == UNEXPECTED_FAILURE


def test_repeated_execution_with_injected_clock_and_id_factory_is_deterministic() -> None:
    observer = _RecordingObserver()
    engine = ObservedRecommendationEngine(
        _StubEngine([_item()]),
        observer,
        engine_name="popularity",
        recommendation_type="popularity",
        request_id_factory=lambda: "fixed-request-id",
        clock=_clock_sequence([0.0, 0.1, 1.0, 1.1]),  # type: ignore[arg-type]
    )

    engine.recommend(RecommendationQuery(limit=1))
    engine.recommend(RecommendationQuery(limit=1))

    first, second = observer.received
    assert first.duration_seconds == pytest.approx(second.duration_seconds)
    assert (first.request_id, first.engine_name, first.recommendation_count, first.success) == (
        second.request_id,
        second.engine_name,
        second.recommendation_count,
        second.success,
    )
