from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from readmatch_ai.domain.recommendation import RecommendationQuery, RecommendationResult
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.recommendation_execution import (
    UNEXPECTED_FAILURE,
    VALIDATION_FAILURE,
    RecommendationExecutionObserver,
    RecommendationExecutionRecord,
)


def _default_request_id() -> str:
    return str(uuid.uuid4())


class ObservedRecommendationEngine(RecommendationEngine):
    """Wraps any RecommendationEngine, emitting one RecommendationExecutionRecord
    per recommend() call to an injected RecommendationExecutionObserver --
    timing, success/failure classification, and fallback detection, all
    without the wrapped engine (or any Application use case) needing to
    know observability exists. Never changes the wrapped engine's return
    value or exception behaviour: a raised exception is always re-raised
    after being observed, unchanged.

    `used_fallback` is derived purely from the query (no book_id and no
    user_id -- see RecommendationExecutionRecord), so this wrapper never
    needs to inspect a concrete engine's internals (e.g.
    HybridRecommendationEngine's candidate sources) to report it.

    `request_id_factory`/`clock` are injectable for deterministic tests;
    they default to `uuid.uuid4`/`time.monotonic`.
    """

    def __init__(
        self,
        inner_engine: RecommendationEngine,
        observer: RecommendationExecutionObserver,
        engine_name: str,
        recommendation_type: str,
        request_id_factory: Callable[[], str] = _default_request_id,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner_engine = inner_engine
        self._observer = observer
        self._engine_name = engine_name
        self._recommendation_type = recommendation_type
        self._request_id_factory = request_id_factory
        self._clock = clock

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        used_fallback = query.book_id is None and query.user_id is None
        start = self._clock()
        try:
            result = self._inner_engine.recommend(query)
        except Exception as exc:
            self._observer.on_execution(
                RecommendationExecutionRecord(
                    request_id=self._request_id_factory(),
                    engine_name=self._engine_name,
                    recommendation_type=self._recommendation_type,
                    duration_seconds=self._clock() - start,
                    recommendation_count=0,
                    used_fallback=used_fallback,
                    success=False,
                    error_classification=(
                        VALIDATION_FAILURE if isinstance(exc, ValueError) else UNEXPECTED_FAILURE
                    ),
                )
            )
            raise

        self._observer.on_execution(
            RecommendationExecutionRecord(
                request_id=self._request_id_factory(),
                engine_name=self._engine_name,
                recommendation_type=self._recommendation_type,
                duration_seconds=self._clock() - start,
                recommendation_count=len(result.recommendation.items),
                used_fallback=used_fallback,
                success=True,
            )
        )
        return result
