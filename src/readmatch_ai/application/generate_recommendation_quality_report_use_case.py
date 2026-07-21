from __future__ import annotations

from collections.abc import Sequence

from readmatch_ai.application.evaluate_recommendation_engine_use_case import (
    EvaluateRecommendationEngineUseCase,
)
from readmatch_ai.domain.evaluation import EvaluationDataset
from readmatch_ai.domain.quality_report import (
    FORMAT_VERSION,
    STANDARD_LIMITATIONS,
    EvaluationRunMetadata,
    MetricComparison,
    QualityReportRunConfig,
    RecommendationEngineQualitySummary,
    RecommendationMetricResult,
    RecommendationQualityReport,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine

# Fixed, deterministic ordering applied everywhere a metric list is
# produced (engine summaries, comparisons, and -- downstream -- exporter
# column order), independent of dict/computation order. Every metric here
# is higher-is-better in this framework; a future lower-is-better metric
# would need its own entry in _HIGHER_IS_BETTER below, not a silent
# global assumption.
_METRIC_NAMES: tuple[str, ...] = (
    "precision_at_k",
    "recall_at_k",
    "map_at_k",
    "ndcg_at_k",
    "hit_rate_at_k",
    "diversity_at_k",
    "coverage",
    "novelty_at_k",
)
_HIGHER_IS_BETTER: dict[str, bool] = dict.fromkeys(_METRIC_NAMES, True)


class GenerateRecommendationQualityReportUseCase:
    """Evaluates every named engine against the same dataset and aggregates a
    structured, comparable RecommendationQualityReport.

    Reuses EvaluateRecommendationEngineUseCase (the existing Evaluation
    Framework) for the actual per-engine evaluation -- this use case only
    aggregates the resulting EvaluationResults into a report; it never
    duplicates ranking, recommendation, or metric-computation logic, and it
    evaluates recommendations already produced by the existing
    RecommendationEngine contract.
    """

    def __init__(
        self,
        evaluate_recommendation_engine_use_case: EvaluateRecommendationEngineUseCase | None = None,
    ) -> None:
        self._evaluate = (
            evaluate_recommendation_engine_use_case or EvaluateRecommendationEngineUseCase()
        )

    def execute(
        self,
        engines: Sequence[tuple[str, RecommendationEngine]],
        dataset: EvaluationDataset,
        k: int,
        config: QualityReportRunConfig,
    ) -> RecommendationQualityReport:
        engine_names = tuple(name for name, _ in engines)
        if config.baseline_engine not in engine_names:
            raise ValueError(
                f"baseline_engine {config.baseline_engine!r} must be one of the evaluated "
                f"engines {engine_names}"
            )

        summaries = tuple(
            self._summarize(name, engine, dataset, k, config) for name, engine in engines
        )
        comparisons = tuple(
            _compare_metric(metric_name, summaries, config.baseline_engine, engine_names)
            for metric_name in _METRIC_NAMES
        )
        metadata = EvaluationRunMetadata(
            run_id=config.run_id,
            generated_at=config.generated_at,
            dataset_id=config.dataset_id,
            k=k,
            catalog_size=config.catalog_size,
            case_count=len(dataset.cases),
            engine_names=engine_names,
            baseline_engine=config.baseline_engine,
            user_count=config.user_count,
            ranking_strategy=config.ranking_strategy,
            reranking_policies=config.reranking_policies,
            embedding_provider=config.embedding_provider,
            embedding_model=config.embedding_model,
            embedding_dimensions=config.embedding_dimensions,
            als_factors=config.als_factors,
            als_iterations=config.als_iterations,
            project_version=config.project_version,
        )
        return RecommendationQualityReport(
            format_version=FORMAT_VERSION,
            metadata=metadata,
            engine_summaries=summaries,
            comparisons=comparisons,
            limitations=STANDARD_LIMITATIONS,
        )

    def _summarize(
        self,
        name: str,
        engine: RecommendationEngine,
        dataset: EvaluationDataset,
        k: int,
        config: QualityReportRunConfig,
    ) -> RecommendationEngineQualitySummary:
        result = self._evaluate.execute(
            engine,
            name,
            dataset,
            k,
            catalog_size=config.catalog_size,
            popularity_by_book_id=config.popularity_by_book_id,
        )
        values: dict[str, float | None] = {
            "precision_at_k": result.precision_at_k,
            "recall_at_k": result.recall_at_k,
            "map_at_k": result.map_at_k,
            "ndcg_at_k": result.ndcg_at_k,
            "hit_rate_at_k": result.hit_rate_at_k,
            "diversity_at_k": result.diversity_at_k,
            "coverage": result.coverage,
            "novelty_at_k": result.novelty_at_k,
        }
        metrics = tuple(
            RecommendationMetricResult(
                name=metric_name,
                value=values[metric_name],
                higher_is_better=_HIGHER_IS_BETTER[metric_name],
            )
            for metric_name in _METRIC_NAMES
        )
        return RecommendationEngineQualitySummary(engine_name=name, metrics=metrics)


def _compare_metric(
    metric_name: str,
    summaries: Sequence[RecommendationEngineQualitySummary],
    baseline_engine: str,
    engine_names: tuple[str, ...],
) -> MetricComparison:
    best_engine = _best_engine(metric_name, summaries, engine_names)
    baseline_value = _find_summary(summaries, baseline_engine).metric(metric_name).value
    deltas: dict[str, float | None] = {}
    for summary in summaries:
        value = summary.metric(metric_name).value
        deltas[summary.engine_name] = (
            value - baseline_value if value is not None and baseline_value is not None else None
        )
    return MetricComparison(
        metric_name=metric_name,
        higher_is_better=_HIGHER_IS_BETTER[metric_name],
        best_engine=best_engine,
        deltas_from_baseline=deltas,
    )


def _best_engine(
    metric_name: str,
    summaries: Sequence[RecommendationEngineQualitySummary],
    engine_names: tuple[str, ...],
) -> str | None:
    # Deterministic tie-break: iterate in the caller's original engine
    # order, not dict/set order, so the first-listed engine among ties
    # always wins, run to run.
    best_name: str | None = None
    best_value: float | None = None
    for name in engine_names:
        value = _find_summary(summaries, name).metric(metric_name).value
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_name = name
    return best_name


def _find_summary(
    summaries: Sequence[RecommendationEngineQualitySummary], engine_name: str
) -> RecommendationEngineQualitySummary:
    for summary in summaries:
        if summary.engine_name == engine_name:
            return summary
    raise KeyError(engine_name)
