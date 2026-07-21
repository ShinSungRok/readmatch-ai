from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from readmatch_ai.domain.quality_report import RecommendationQualityReport


@dataclass(frozen=True)
class RegressionThreshold:
    """One quality gate for a single engine/metric pair.

    At least one of `minimum_value` (an absolute floor) or
    `max_regression_from_baseline` (the metric must not fall more than this
    far below the report's baseline engine's value for the same metric)
    must be set. Both may be set at once. Deliberately scoped to a single
    report's own baseline comparison rather than a persisted historical
    run, so this stays a pure, self-contained, CI-suitable check with no
    external storage dependency.
    """

    engine_name: str
    metric_name: str
    minimum_value: float | None = None
    max_regression_from_baseline: float | None = None

    def __post_init__(self) -> None:
        if self.minimum_value is None and self.max_regression_from_baseline is None:
            raise ValueError(
                "RegressionThreshold requires at least one of minimum_value or "
                "max_regression_from_baseline"
            )


@dataclass(frozen=True)
class RegressionCheckFailure:
    """One violated (or unverifiable) threshold, with a human-readable explanation."""

    engine_name: str
    metric_name: str
    message: str


@dataclass(frozen=True)
class RegressionCheckResult:
    """Outcome of checking a RecommendationQualityReport against a set of thresholds."""

    passed: bool
    failures: tuple[RegressionCheckFailure, ...]


def check_recommendation_quality_regressions(
    report: RecommendationQualityReport, thresholds: Sequence[RegressionThreshold]
) -> RegressionCheckResult:
    """Deterministically check `report` against `thresholds`.

    An empty `thresholds` sequence always passes (nothing to check). Every
    threshold is evaluated independently and in order, so all failures are
    reported together, not just the first one -- useful for CI logs. A
    threshold whose engine wasn't evaluated, whose metric name is unknown,
    or whose referenced value(s) are None (insufficient evidence) is itself
    a failure with a clear explanation -- an operator who wrote the
    threshold expected it to be checkable.
    """
    failures: list[RegressionCheckFailure] = []
    for threshold in thresholds:
        failure = _check_one(report, threshold)
        if failure is not None:
            failures.append(failure)
    return RegressionCheckResult(passed=not failures, failures=tuple(failures))


def _check_one(
    report: RecommendationQualityReport, threshold: RegressionThreshold
) -> RegressionCheckFailure | None:
    try:
        summary = report.summary_for(threshold.engine_name)
    except KeyError:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"engine {threshold.engine_name!r} was not evaluated in this report",
        )
    try:
        metric = summary.metric(threshold.metric_name)
    except KeyError:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"metric {threshold.metric_name!r} was not computed for engine "
            f"{threshold.engine_name!r}",
        )
    if metric.value is None:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"{threshold.metric_name} has no value for engine {threshold.engine_name!r} "
            "(insufficient evidence) -- cannot verify threshold",
        )

    if threshold.minimum_value is not None and metric.value < threshold.minimum_value:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"{threshold.metric_name} for {threshold.engine_name!r} is "
            f"{metric.value:.4f}, below the minimum acceptable value "
            f"{threshold.minimum_value:.4f}",
        )

    if threshold.max_regression_from_baseline is not None:
        baseline_failure = _check_baseline_regression(report, threshold, metric.value)
        if baseline_failure is not None:
            return baseline_failure

    return None


def _check_baseline_regression(
    report: RecommendationQualityReport, threshold: RegressionThreshold, value: float
) -> RegressionCheckFailure | None:
    assert threshold.max_regression_from_baseline is not None  # narrowed by caller
    baseline_engine = report.metadata.baseline_engine
    try:
        baseline_value = report.summary_for(baseline_engine).metric(threshold.metric_name).value
    except KeyError:
        baseline_value = None
    if baseline_value is None:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"baseline engine {baseline_engine!r} has no value for {threshold.metric_name} "
            "-- cannot verify regression tolerance",
        )
    floor = baseline_value - threshold.max_regression_from_baseline
    if value < floor:
        return RegressionCheckFailure(
            threshold.engine_name,
            threshold.metric_name,
            f"{threshold.metric_name} for {threshold.engine_name!r} is {value:.4f}, more than "
            f"{threshold.max_regression_from_baseline:.4f} below baseline {baseline_engine!r}'s "
            f"{baseline_value:.4f} (floor {floor:.4f})",
        )
    return None
