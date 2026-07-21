import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.recommendation import RecommendationItem, RecommendationQuery

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_run_demo_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_demo_script", _REPO_ROOT / "scripts" / "run_demo.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # run_demo.py defines a @dataclass at module scope; dataclasses resolves
    # its module's globals via sys.modules[__module__], so the module must be
    # registered there before exec_module runs, or that lookup returns None.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_run_demo = _load_run_demo_module()
main = _run_demo.main


def test_demo_seeds_and_serves_all_three_recommendation_strategies(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context = ApplicationContext.create()

    exit_code = main(["--limit", "3", "--k", "3"], application_context=context)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Seeded 8 demo books across 3 categories." in output
    assert "[Popularity]" in output
    assert "[Semantic]" in output
    assert "[Hybrid]" in output
    assert "[Hybrid (Weighted Score Fusion)]" in output
    assert "[Hybrid (Reciprocal Rank Fusion)]" in output
    assert "[Hybrid (Weighted, no re-ranking)]" in output
    assert "[Hybrid (Weighted) + Re-ranking]" in output
    assert "Offline evaluation" in output
    for engine_name in (
        "popularity",
        "semantic",
        "als",
        "hybrid_weighted",
        "hybrid_rrf",
        "hybrid_reranked",
    ):
        assert engine_name in output


def test_demo_actually_persists_books_through_the_application_context() -> None:
    context = ApplicationContext.create()

    main([], application_context=context)

    clean_code = context.get_book_by_isbn_use_case.execute("9780000000019")
    assert clean_code is not None
    assert clean_code.title.value == "Clean Code"
    assert context.book_embedding_repository.get_by_book_id(clean_code.id) is not None


def test_demo_recommendation_endpoints_return_valid_json_via_the_real_api() -> None:
    context = ApplicationContext.create()

    books = _run_demo.seed_demo_dataset(context)
    app = _run_demo.create_app()
    app.dependency_overrides[_run_demo.get_application_context] = lambda: context
    client = _run_demo.TestClient(app)

    spotlight = books[0]
    response = client.get(f"/recommendations/semantic/{spotlight.id.value}", params={"limit": 3})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) <= 3
    assert all(item["book"]["id"] != str(spotlight.id.value) for item in items)


def test_evaluation_dataset_groups_books_by_category() -> None:
    context = ApplicationContext.create()
    books = _run_demo.seed_demo_dataset(context)
    user_id = _run_demo._user_id(_run_demo.DEMO_USER_LABEL)

    dataset = _run_demo._build_evaluation_dataset(books, user_id)

    assert len(dataset.cases) == len(books)
    software_engineering_case = next(
        case for case in dataset.cases if case.book_id == books[0].id
    )
    assert len(software_engineering_case.relevant_book_ids) == 2
    assert software_engineering_case.user_id == user_id


def test_als_engine_recommends_effective_java_for_alice_via_shared_reader_correlation() -> None:
    """Sanity-checks the demo's own seeded ALS training signal.

    alice and bob both read "The Pragmatic Programmer"; bob also read
    "Effective Java", which alice hasn't -- ALS should be able to surface it
    for alice via that shared-reader correlation.
    """
    context = ApplicationContext.create()
    books = _run_demo.seed_demo_dataset(context)
    als_engine = _run_demo._build_als_engine(context)
    alice = _run_demo._user_id("alice")

    result = als_engine.recommend(RecommendationQuery(limit=len(books), user_id=alice))

    effective_java = next(book for book in books if book.title.value == "Effective Java")
    recommended_ids = {item.book.id for item in result.recommendation.items}
    assert effective_java.id in recommended_ids


def test_reranked_engine_preserves_count_and_boosts_a_novel_book() -> None:
    """Sanity-checks _build_reranked_engine's composition against the demo's
    own seeded data: re-ranking must return exactly as many items as
    requested (when enough candidates exist), and NoveltyBoostPolicy must
    raise "Effective Java"'s score relative to the un-reranked Hybrid list
    (alice hasn't read it; only bob has). Book ids are random per run, so
    this compares scores for the same title rather than asserting on list
    order, which can tie-break differently run to run.
    """
    context = ApplicationContext.create()
    books = _run_demo.seed_demo_dataset(context)
    als_engine = _run_demo._build_als_engine(context)
    hybrid_weighted_engine, _ = _run_demo._build_hybrid_engines(context, als_engine)
    reranked_engine = _run_demo._build_reranked_engine(context, hybrid_weighted_engine)
    spotlight = next(book for book in books if book.title.value == "Clean Code")
    alice = _run_demo._user_id("alice")
    query = RecommendationQuery(limit=len(books), book_id=spotlight.id, user_id=alice)

    plain_items = hybrid_weighted_engine.recommend(query).recommendation.items
    reranked_items = reranked_engine.recommend(query).recommendation.items

    assert len(reranked_items) == len(plain_items)

    def _score_of(items: list[RecommendationItem], title: str) -> float:
        return next(item.score for item in items if item.book.title.value == title)

    assert _score_of(reranked_items, "Effective Java") > _score_of(plain_items, "Effective Java")
