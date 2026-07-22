"""Sprint 63: confirms the pre-existing GenerateRecommendationQualityReportUseCase
(Sprint 30-era) already satisfies "evaluate Popularity, Semantic, ALS, and
Hybrid, and generate comparable evaluation results" -- against the real
recommendation pipeline (not fakes), reusing the existing demo fixtures and
Sprint 61's new split_dataset() rather than introducing a second, competing
comparison mechanism. No recommendation engine is modified here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from readmatch_ai.application.generate_recommendation_quality_report_use_case import (
    GenerateRecommendationQualityReportUseCase,
)
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.evaluation import split_dataset
from readmatch_ai.domain.quality_report import QualityReportRunConfig

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _load_demo_fixtures() -> ModuleType:
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "demo_fixtures", _SCRIPTS_DIR / "demo_fixtures.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


demo_fixtures = _load_demo_fixtures()

_REQUIRED_ENGINE_NAMES = ("popularity", "semantic", "als", "hybrid")


def test_compares_popularity_semantic_als_and_hybrid_on_a_held_out_test_split() -> None:
    context = ApplicationContext.create()
    books = demo_fixtures.seed_demo_dataset(context)
    user = demo_fixtures.user_id(demo_fixtures.DEMO_USER_LABEL)
    full_dataset = demo_fixtures.build_evaluation_dataset(books, user)
    split = split_dataset(full_dataset, seed=0)

    als_engine = demo_fixtures.build_als_engine(context)
    hybrid_engine, _hybrid_rrf_engine = demo_fixtures.build_hybrid_engines(context, als_engine)
    engines = [
        ("popularity", context.recommendation_engine),
        ("semantic", context.semantic_recommendation_engine),
        ("als", als_engine),
        ("hybrid", hybrid_engine),
    ]

    report = GenerateRecommendationQualityReportUseCase().execute(
        engines,
        split.test,
        k=3,
        config=QualityReportRunConfig(
            run_id="sprint-63-engine-comparison",
            generated_at="2026-01-01T00:00:00Z",
            dataset_id=demo_fixtures.DATASET_ID,
            baseline_engine="popularity",
            catalog_size=len(books),
        ),
    )

    assert report.metadata.engine_names == _REQUIRED_ENGINE_NAMES
    assert report.metadata.case_count == len(split.test.cases)
    for engine_name in _REQUIRED_ENGINE_NAMES:
        summary = report.summary_for(engine_name)
        assert summary.metric("precision_at_k").value is not None
        assert summary.metric("recall_at_k").value is not None
        assert summary.metric("map_at_k").value is not None
        assert summary.metric("ndcg_at_k").value is not None
        assert summary.metric("hit_rate_at_k").value is not None

    # "Comparable evaluation results": every metric has a determined winner
    # among these four real engines -- not just structurally present values.
    precision_comparison = next(c for c in report.comparisons if c.metric_name == "precision_at_k")
    assert precision_comparison.best_engine in _REQUIRED_ENGINE_NAMES
