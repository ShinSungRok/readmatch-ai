from __future__ import annotations

import json
from typing import Any

from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    MetricComparison,
    RecommendationEngineQualitySummary,
    RecommendationQualityReport,
)
from readmatch_ai.domain.quality_reporter import RecommendationQualityReporter


class JsonRecommendationQualityReporter(RecommendationQualityReporter):
    """Renders a RecommendationQualityReport as JSON.

    Standard-library `json` module only. Field order within each object is
    fixed by construction below (never derived from dict/dataclass
    iteration order), so repeated renders of an unchanged report are
    byte-identical. A metric/delta with no computed value serializes as
    JSON `null` -- the same "not computed" distinction the domain model
    itself makes (RecommendationMetricResult.value: float | None) -- rather
    than CsvRecommendationQualityReporter's own empty-string convention,
    since JSON has a native representation for it.
    """

    def render(self, report: RecommendationQualityReport) -> str:
        document = {
            "format_version": report.format_version,
            "metadata": _metadata_dict(report.metadata),
            "engine_summaries": [_summary_dict(summary) for summary in report.engine_summaries],
            "comparisons": [_comparison_dict(comparison) for comparison in report.comparisons],
            "limitations": list(report.limitations),
        }
        return json.dumps(document, indent=2) + "\n"


def _metadata_dict(metadata: EvaluationRunMetadata) -> dict[str, Any]:
    return {
        "run_id": metadata.run_id,
        "generated_at": metadata.generated_at,
        "dataset_id": metadata.dataset_id,
        "k": metadata.k,
        "catalog_size": metadata.catalog_size,
        "case_count": metadata.case_count,
        "engine_names": list(metadata.engine_names),
        "baseline_engine": metadata.baseline_engine,
        "user_count": metadata.user_count,
        "ranking_strategy": metadata.ranking_strategy,
        "reranking_policies": (
            list(metadata.reranking_policies) if metadata.reranking_policies is not None else None
        ),
        "embedding_provider": metadata.embedding_provider,
        "embedding_model": metadata.embedding_model,
        "embedding_dimensions": metadata.embedding_dimensions,
        "als_factors": metadata.als_factors,
        "als_iterations": metadata.als_iterations,
        "project_version": metadata.project_version,
    }


def _summary_dict(summary: RecommendationEngineQualitySummary) -> dict[str, Any]:
    return {
        "engine_name": summary.engine_name,
        "metrics": [
            {
                "name": metric.name,
                "value": metric.value,
                "higher_is_better": metric.higher_is_better,
            }
            for metric in summary.metrics
        ],
    }


def _comparison_dict(comparison: MetricComparison) -> dict[str, Any]:
    return {
        "metric_name": comparison.metric_name,
        "higher_is_better": comparison.higher_is_better,
        "best_engine": comparison.best_engine,
        "deltas_from_baseline": dict(comparison.deltas_from_baseline),
    }
