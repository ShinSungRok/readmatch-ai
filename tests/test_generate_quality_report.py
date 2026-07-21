import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from readmatch_ai.domain.quality_regression import RegressionThreshold

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _load_module(name: str) -> ModuleType:
    # Both run_demo.py and generate_quality_report.py import shared fixtures
    # via a bare `from demo_fixtures import ...`, which resolves
    # automatically when run directly (Python puts the script's own
    # directory on sys.path[0]) but needs scripts/ on sys.path explicitly
    # when loaded here via importlib instead.
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))

    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_generate_quality_report = _load_module("generate_quality_report")
main = _generate_quality_report.main


def test_main_succeeds_and_writes_markdown_and_csv_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"

    exit_code = main(["--output-dir", str(output_dir)])

    assert exit_code == 0
    markdown_path = output_dir / "quality_report.md"
    csv_path = output_dir / "quality_report.csv"
    assert markdown_path.exists()
    assert csv_path.exists()
    markdown_text = markdown_path.read_text()
    assert "# Recommendation Quality Report" in markdown_text
    assert "hybrid_reranked" in markdown_text
    csv_text = csv_path.read_text()
    assert csv_text.splitlines()[0].startswith("engine,")


def test_main_creates_a_nested_output_directory_that_does_not_yet_exist(tmp_path: Path) -> None:
    output_dir = tmp_path / "a" / "b" / "c"
    assert not output_dir.exists()

    exit_code = main(["--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "quality_report.md").exists()


def test_main_evaluates_all_six_comparison_engines(tmp_path: Path) -> None:
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    csv_text = (tmp_path / "quality_report.csv").read_text()
    for engine_name in (
        "popularity",
        "semantic",
        "als",
        "hybrid_weighted",
        "hybrid_rrf",
        "hybrid_reranked",
    ):
        assert engine_name in csv_text


def test_main_prints_a_concise_execution_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["--output-dir", str(tmp_path)])

    output = capsys.readouterr().out
    assert "Recommendation Quality Report" in output
    assert "Regression check:" in output
    assert str(tmp_path) in output


def test_main_returns_zero_when_default_regression_thresholds_are_satisfied(
    tmp_path: Path,
) -> None:
    # The committed default thresholds are calibrated against this repo's
    # own deterministic demo dataset, so the default run must pass.
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0


def test_main_returns_nonzero_when_a_regression_threshold_is_violated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        _generate_quality_report,
        "DEFAULT_REGRESSION_THRESHOLDS",
        (RegressionThreshold("popularity", "precision_at_k", minimum_value=0.99),),
    )

    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "Regression check: FAILED" in output
    assert "popularity" in output
    assert "precision_at_k" in output


def test_repeated_report_generation_is_deterministic_given_a_fixed_run_id_and_timestamp(
    tmp_path: Path,
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    def _args(output_dir: Path) -> list[str]:
        return [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "fixed-run",
            "--generated-at",
            "2026-01-01T00:00:00Z",
        ]

    assert main(_args(first_dir)) == 0
    assert main(_args(second_dir)) == 0

    assert (first_dir / "quality_report.md").read_text() == (
        second_dir / "quality_report.md"
    ).read_text()
    assert (first_dir / "quality_report.csv").read_text() == (
        second_dir / "quality_report.csv"
    ).read_text()
