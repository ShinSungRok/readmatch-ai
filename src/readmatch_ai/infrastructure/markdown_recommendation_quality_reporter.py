from __future__ import annotations

from readmatch_ai.domain.quality_report import (
    EvaluationRunMetadata,
    MetricComparison,
    RecommendationQualityReport,
)
from readmatch_ai.domain.quality_reporter import RecommendationQualityReporter

# One-line, honest interpretation per metric -- keeps a reader from having
# to cross-reference source code to understand a column heading. Mirrors
# each metric function's own docstring, kept short for table/note use.
_METRIC_NOTES: dict[str, str] = {
    "precision_at_k": "Fraction of the top-K recommendations that are relevant.",
    "recall_at_k": "Fraction of all relevant books surfaced in the top-K.",
    "map_at_k": "Mean Average Precision@K -- rewards relevant books appearing earlier.",
    "ndcg_at_k": "Normalized Discounted Cumulative Gain@K -- rank-sensitive relevance.",
    "hit_rate_at_k": "Fraction of cases with at least one relevant book in the top-K.",
    "diversity_at_k": "Fraction of distinct categories within the top-K recommendation list.",
    "coverage": "Fraction of the whole catalog reached by this engine across the run.",
    "novelty_at_k": (
        "Mean self-information novelty of the top-K (higher = less popular / more novel); "
        "N/A where no popularity evidence exists."
    ),
}


class MarkdownRecommendationQualityReporter(RecommendationQualityReporter):
    """Renders a RecommendationQualityReport as a Markdown document.

    Standard-library string formatting only -- no Markdown library
    dependency.
    """

    def render(self, report: RecommendationQualityReport) -> str:
        sections = [
            "# Recommendation Quality Report",
            "",
            _render_metadata(report.metadata),
            "## Engine Comparison",
            "",
            _render_comparison_table(report),
            "## Best-Performing Engine by Metric",
            "",
            _render_best_engine_table(report.comparisons),
            "## Baseline Deltas",
            "",
            _render_baseline_deltas(report),
            "## Metric Interpretation",
            "",
            _render_metric_notes(report.comparisons),
            "## Limitations",
            "",
            _render_limitations(report.limitations),
        ]
        return "\n".join(sections)


def _fmt(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def _render_metadata(metadata: EvaluationRunMetadata) -> str:
    rows = [
        ("Run ID", metadata.run_id),
        ("Generated at", metadata.generated_at),
        ("Dataset", metadata.dataset_id),
        ("K", str(metadata.k)),
        ("Catalog size", str(metadata.catalog_size)),
        ("Evaluation cases", str(metadata.case_count)),
        ("Users", str(metadata.user_count) if metadata.user_count is not None else "N/A"),
        ("Engines evaluated", ", ".join(metadata.engine_names)),
        ("Baseline engine", metadata.baseline_engine),
        ("Ranking strategy", metadata.ranking_strategy or "N/A"),
        (
            "Re-ranking policies",
            ", ".join(metadata.reranking_policies) if metadata.reranking_policies else "N/A",
        ),
        ("Embedding provider", metadata.embedding_provider or "N/A"),
        ("Embedding model", metadata.embedding_model or "N/A"),
        (
            "Embedding dimensions",
            str(metadata.embedding_dimensions) if metadata.embedding_dimensions else "N/A",
        ),
        ("ALS factors", str(metadata.als_factors) if metadata.als_factors else "N/A"),
        ("ALS iterations", str(metadata.als_iterations) if metadata.als_iterations else "N/A"),
        ("Project version", metadata.project_version or "N/A"),
    ]
    lines = ["## Run Metadata", "", "| Field | Value |", "|---|---|"]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.append("")
    return "\n".join(lines)


def _metric_names(report: RecommendationQualityReport) -> tuple[str, ...]:
    if not report.engine_summaries:
        return ()
    return tuple(metric.name for metric in report.engine_summaries[0].metrics)


def _render_comparison_table(report: RecommendationQualityReport) -> str:
    metric_names = _metric_names(report)
    header = "| Engine | " + " | ".join(metric_names) + " |"
    separator = "|---|" + "|".join("---" for _ in metric_names) + "|"
    lines = [header, separator]
    for summary in report.engine_summaries:
        values = " | ".join(_fmt(summary.metric(name).value) for name in metric_names)
        lines.append(f"| {summary.engine_name} | {values} |")
    lines.append("")
    return "\n".join(lines)


def _render_best_engine_table(comparisons: tuple[MetricComparison, ...]) -> str:
    lines = ["| Metric | Best Engine | Higher is Better |", "|---|---|---|"]
    for comparison in comparisons:
        best = comparison.best_engine or "N/A"
        lines.append(f"| {comparison.metric_name} | {best} | {comparison.higher_is_better} |")
    lines.append("")
    return "\n".join(lines)


def _render_baseline_deltas(report: RecommendationQualityReport) -> str:
    metric_names = _metric_names(report)
    deltas_by_metric = {c.metric_name: c.deltas_from_baseline for c in report.comparisons}
    header = "| Engine | " + " | ".join(metric_names) + " |"
    separator = "|---|" + "|".join("---" for _ in metric_names) + "|"
    lines = [header, separator]
    for summary in report.engine_summaries:
        values = " | ".join(
            _fmt(deltas_by_metric[name].get(summary.engine_name)) for name in metric_names
        )
        lines.append(f"| {summary.engine_name} | {values} |")
    lines.append(
        "\n_Delta = engine value − baseline "
        f"({report.metadata.baseline_engine!r}) value. Positive means better than baseline "
        "when higher-is-better. This is a plain numeric difference, not a statistical "
        "significance test._"
    )
    lines.append("")
    return "\n".join(lines)


def _render_metric_notes(comparisons: tuple[MetricComparison, ...]) -> str:
    lines = [f"- **{c.metric_name}**: {_METRIC_NOTES.get(c.metric_name, '')}" for c in comparisons]
    lines.append("")
    return "\n".join(lines)


def _render_limitations(limitations: tuple[str, ...]) -> str:
    return "\n".join(f"- {limitation}" for limitation in limitations)
