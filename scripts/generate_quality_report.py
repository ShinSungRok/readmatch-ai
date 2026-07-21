#!/usr/bin/env python3
"""Generates a recommendation quality report comparing all current
recommendation engines against the deterministic demo dataset, writes it as
Markdown and CSV, and runs a lightweight regression check suitable for CI.

Contains no recommendation, metric, aggregation, or comparison logic itself
-- that all lives in GenerateRecommendationQualityReportUseCase (Application)
and the Domain evaluation/quality_report/quality_regression modules. This
script only composes the deterministic in-memory ApplicationContext + the
standard 6-engine comparison set (both via scripts/demo_fixtures.py, shared
with scripts/run_demo.py), invokes the reporting use case, delegates
rendering to the Markdown/CSV adapters, writes the results to disk, and
prints a summary.

Usage:
    python scripts/generate_quality_report.py
    python scripts/generate_quality_report.py --k 5 --output-dir reports
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import demo_fixtures

import readmatch_ai
from readmatch_ai.application.generate_recommendation_quality_report_use_case import (
    GenerateRecommendationQualityReportUseCase,
)
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.config import EmbeddingGeneratorConfig, HybridRankingConfig
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.quality_regression import (
    RegressionCheckResult,
    RegressionThreshold,
    check_recommendation_quality_regressions,
)
from readmatch_ai.domain.quality_report import QualityReportRunConfig, RecommendationQualityReport
from readmatch_ai.infrastructure.als_model import _DEFAULT_FACTORS, _DEFAULT_ITERATIONS
from readmatch_ai.infrastructure.csv_recommendation_quality_reporter import (
    CsvRecommendationQualityReporter,
)
from readmatch_ai.infrastructure.markdown_recommendation_quality_reporter import (
    MarkdownRecommendationQualityReporter,
)

# Matches the exact policy composition demo_fixtures.build_reranked_engine
# wires (PopularityPenaltyPolicy, NoveltyBoostPolicy, MMRDiversityPolicy, in
# that order) -- report metadata only, not re-derived at runtime, since
# RerankingPolicy has no name/label of its own to introspect.
_RERANKING_POLICIES: tuple[str, ...] = ("popularity_penalty", "novelty_boost", "mmr_diversity")

# A conservative default regression gate against this repo's own committed,
# deterministic demo dataset -- realistic for *this* fixed dataset, not a
# guess at production quality. hybrid_reranked is checked specifically since
# it's the full pipeline (Hybrid + re-ranking) the personalized API serves.
DEFAULT_REGRESSION_THRESHOLDS: tuple[RegressionThreshold, ...] = (
    RegressionThreshold("hybrid_reranked", "precision_at_k", minimum_value=0.05),
    RegressionThreshold("hybrid_reranked", "hit_rate_at_k", minimum_value=0.2),
    RegressionThreshold("hybrid_reranked", "recall_at_k", max_regression_from_baseline=0.5),
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    context = ApplicationContext.create()
    books = demo_fixtures.seed_demo_dataset(context)
    dataset = demo_fixtures.build_evaluation_dataset(
        books, demo_fixtures.user_id(demo_fixtures.DEMO_USER_LABEL)
    )
    engines = demo_fixtures.build_comparison_engines(context)

    config = _build_run_config(context, books, args)
    report = GenerateRecommendationQualityReportUseCase().execute(
        engines, dataset, args.k, config
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "quality_report.md"
    csv_path = output_dir / "quality_report.csv"
    markdown_path.write_text(MarkdownRecommendationQualityReporter().render(report))
    csv_path.write_text(CsvRecommendationQualityReporter().render(report))

    regression_result = check_recommendation_quality_regressions(
        report, DEFAULT_REGRESSION_THRESHOLDS
    )
    _print_summary(report, regression_result, markdown_path, csv_path)

    return 0 if regression_result.passed else 1


def _build_run_config(
    context: ApplicationContext, books: list[Book], args: argparse.Namespace
) -> QualityReportRunConfig:
    popularity_by_book_id = {
        popularity.book_id: popularity.loan_count
        for popularity in context.book_popularity_repository.top_by_loan_count(len(books))
    }
    # Real, observed evidence (not guessed): whatever the embedding
    # generator actually produced for a seeded book.
    sample_embedding = context.book_embedding_repository.get_by_book_id(books[0].id)
    embedding_config = EmbeddingGeneratorConfig.from_env()
    ranking_config = HybridRankingConfig.from_env()
    user_count = len({interaction.user_label for interaction in demo_fixtures.SEED_INTERACTIONS})

    return QualityReportRunConfig(
        run_id=args.run_id or str(uuid.uuid4()),
        generated_at=args.generated_at or datetime.now(UTC).isoformat(),
        dataset_id=demo_fixtures.DATASET_ID,
        baseline_engine=args.baseline,
        catalog_size=len(books),
        user_count=user_count,
        popularity_by_book_id=popularity_by_book_id,
        # HYBRID_RANKING_STRATEGY's process-wide default -- this report also
        # separately compares hybrid_weighted/hybrid_rrf as two named
        # engines regardless of which one this reflects.
        ranking_strategy=ranking_config.strategy,
        reranking_policies=_RERANKING_POLICIES,
        embedding_provider=embedding_config.backend,
        embedding_model=sample_embedding.model_name if sample_embedding is not None else None,
        embedding_dimensions=(
            sample_embedding.dimensions if sample_embedding is not None else None
        ),
        als_factors=_DEFAULT_FACTORS,
        als_iterations=_DEFAULT_ITERATIONS,
        project_version=readmatch_ai.__version__,
    )


def _print_summary(
    report: RecommendationQualityReport,
    regression_result: RegressionCheckResult,
    markdown_path: Path,
    csv_path: Path,
) -> None:
    print(f"Recommendation Quality Report (run_id={report.metadata.run_id})")
    print(f"  Dataset: {report.metadata.dataset_id} ({report.metadata.case_count} cases)")
    print(f"  Engines: {', '.join(report.metadata.engine_names)}")
    print(f"  K={report.metadata.k}  Baseline={report.metadata.baseline_engine}")
    print(f"  Markdown: {markdown_path}")
    print(f"  CSV: {csv_path}")
    print()
    if regression_result.passed:
        print("Regression check: PASSED")
    else:
        print("Regression check: FAILED")
        for failure in regression_result.failures:
            print(f"  - [{failure.engine_name} / {failure.metric_name}] {failure.message}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a recommendation quality report (Markdown + CSV)."
    )
    parser.add_argument(
        "--k", type=int, default=5, help="Top-K for evaluation metrics (default: 5)"
    )
    parser.add_argument(
        "--baseline", default="popularity", help="Baseline engine name (default: popularity)"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory for the report files (default: reports)",
    )
    parser.add_argument(
        "--run-id", default=None, help="Override the generated run id (for deterministic runs)"
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override the generated timestamp, ISO 8601 (for deterministic runs)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
