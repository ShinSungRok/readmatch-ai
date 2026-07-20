import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from readmatch_ai.application_context import ApplicationContext

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
    assert "Offline evaluation" in output
    for engine_name in ("popularity", "semantic", "hybrid"):
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

    dataset = _run_demo._build_evaluation_dataset(books)

    assert len(dataset.cases) == len(books)
    software_engineering_case = next(
        case for case in dataset.cases if case.book_id == books[0].id
    )
    assert len(software_engineering_case.relevant_book_ids) == 2
