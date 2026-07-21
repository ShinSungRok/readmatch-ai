from __future__ import annotations

import csv
import io

from readmatch_ai.domain.quality_report import RecommendationQualityReport
from readmatch_ai.domain.quality_reporter import RecommendationQualityReporter


class CsvRecommendationQualityReporter(RecommendationQualityReporter):
    """Renders a RecommendationQualityReport as CSV: one row per engine.

    Standard-library `csv` module only. Column order is `engine`, then each
    metric (in the report's own, already-deterministic metric order), then
    each metric's `<metric>_delta_from_baseline` -- stable across runs since
    it only depends on the report's own metric ordering, never on dict/set
    iteration order.
    """

    def render(self, report: RecommendationQualityReport) -> str:
        metric_names = (
            tuple(metric.name for metric in report.engine_summaries[0].metrics)
            if report.engine_summaries
            else ()
        )
        deltas_by_metric = {
            comparison.metric_name: comparison.deltas_from_baseline
            for comparison in report.comparisons
        }

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        header = (
            ["engine"]
            + list(metric_names)
            + [f"{name}_delta_from_baseline" for name in metric_names]
        )
        writer.writerow(header)
        for summary in report.engine_summaries:
            values = [_fmt(summary.metric(name).value) for name in metric_names]
            deltas = [
                _fmt(deltas_by_metric[name].get(summary.engine_name)) for name in metric_names
            ]
            writer.writerow([summary.engine_name, *values, *deltas])
        return buffer.getvalue()


def _fmt(value: float | None) -> str:
    return "" if value is None else str(value)
