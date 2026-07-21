from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId

FORMAT_VERSION = "1.0"

# Fixed, deterministic set of caveats every report carries -- honest by
# construction rather than by author discipline. Mirrors README's
# documented limitations verbatim so both stay in sync from one source.
STANDARD_LIMITATIONS: tuple[str, ...] = (
    "Offline ground truth may not represent actual user intent.",
    "Deterministic demo data is for reproducibility, not production benchmarking.",
    "Higher diversity may trade off against relevance.",
    "Higher offline metric values do not guarantee a better online user experience.",
    "This report does not replace online experiments or A/B testing.",
)


@dataclass(frozen=True)
class RecommendationMetricResult:
    """One metric's value for one engine, with enough metadata to compare across engines.

    `value` is None when the metric could not be computed for this engine
    (e.g. novelty with no popularity evidence) -- distinguished from a
    fabricated 0.0. `higher_is_better` is carried per-result rather than
    assumed globally, since a future metric could legitimately be
    lower-is-better.
    """

    name: str
    value: float | None
    higher_is_better: bool


@dataclass(frozen=True)
class RecommendationEngineQualitySummary:
    """One engine's full set of metric results for one evaluation run."""

    engine_name: str
    metrics: tuple[RecommendationMetricResult, ...]

    def metric(self, name: str) -> RecommendationMetricResult:
        for result in self.metrics:
            if result.name == name:
                return result
        raise KeyError(f"No metric {name!r} in summary for engine {self.engine_name!r}")


@dataclass(frozen=True)
class EvaluationRunMetadata:
    """Enough context to understand and reproduce a RecommendationQualityReport.

    `run_id`/`generated_at` are always injected by the caller (see
    QualityReportRunConfig) rather than computed here, so report generation
    stays deterministic and testable without depending on the real clock or
    a random id generator. Configuration fields are all optional: populated
    from whichever existing config/composition the caller already resolved
    (HybridRankingConfig, EmbeddingGeneratorConfig, als_model's factors/
    iterations, ...), never re-derived or guessed by this module.
    """

    run_id: str
    generated_at: str
    dataset_id: str
    k: int
    catalog_size: int
    case_count: int
    engine_names: tuple[str, ...]
    baseline_engine: str
    user_count: int | None = None
    ranking_strategy: str | None = None
    reranking_policies: tuple[str, ...] | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    als_factors: int | None = None
    als_iterations: int | None = None
    project_version: str | None = None


@dataclass(frozen=True)
class MetricComparison:
    """Cross-engine comparison for one metric: who's best, and each engine's delta from baseline.

    `best_engine` is None only when no evaluated engine produced a value for
    this metric at all. Ties are broken by engine input order (the first
    engine, in the order passed to GenerateRecommendationQualityReportUseCase,
    wins a tie) -- deterministic, and independent of dict/set iteration
    order. `deltas_from_baseline` omits statistical-significance language by
    design: it reports a plain numeric difference, nothing more.
    """

    metric_name: str
    higher_is_better: bool
    best_engine: str | None
    deltas_from_baseline: Mapping[str, float | None]


@dataclass(frozen=True)
class RecommendationQualityReport:
    """A structured, format-independent recommendation quality comparison.

    Deliberately holds no Markdown/CSV/filesystem concept -- serialization
    is entirely the concern of a RecommendationQualityReporter adapter (see
    quality_reporter.py) given this report as input.
    """

    format_version: str
    metadata: EvaluationRunMetadata
    engine_summaries: tuple[RecommendationEngineQualitySummary, ...]
    comparisons: tuple[MetricComparison, ...]
    limitations: tuple[str, ...]

    def summary_for(self, engine_name: str) -> RecommendationEngineQualitySummary:
        for summary in self.engine_summaries:
            if summary.engine_name == engine_name:
                return summary
        raise KeyError(f"No engine summary for {engine_name!r}")


@dataclass(frozen=True)
class QualityReportRunConfig:
    """External inputs GenerateRecommendationQualityReportUseCase cannot derive
    from the engines/dataset it's given -- run identity, and whatever
    configuration/evidence the caller already has on hand.
    """

    run_id: str
    generated_at: str
    dataset_id: str
    baseline_engine: str
    catalog_size: int
    user_count: int | None = None
    popularity_by_book_id: Mapping[BookId, int] | None = None
    ranking_strategy: str | None = None
    reranking_policies: tuple[str, ...] | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    als_factors: int | None = None
    als_iterations: int | None = None
    project_version: str | None = None
