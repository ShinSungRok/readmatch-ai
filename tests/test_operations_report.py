import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _load_module(name: str) -> ModuleType:
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))

    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_operations_report = _load_module("operations_report")
main = _operations_report.main


def test_main_returns_zero_for_a_valid_default_application() -> None:
    assert main([]) == 0


def test_main_prints_the_operations_summary(capsys: pytest.CaptureFixture[str]) -> None:
    main([])

    output = capsys.readouterr().out
    assert "mode: development" in output
    assert "healthy: True" in output
    assert "ready: True" in output
    assert "Operational." in output


def test_main_omits_deployment_valid_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    main([])

    assert "deployment_valid" not in capsys.readouterr().out


def test_main_includes_deployment_check_when_requested(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["--include-deployment-check"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "deployment_valid: True" in output


def test_main_returns_nonzero_and_reports_gracefully_when_startup_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    exit_code = main([])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Could not build ApplicationContext" in output
    assert "RuntimeBootstrapFailure" in output


def test_main_is_deterministic_across_repeated_calls(
    capsys: pytest.CaptureFixture[str],
) -> None:
    first_exit = main([])
    first_output = capsys.readouterr().out
    second_exit = main([])
    second_output = capsys.readouterr().out

    assert first_exit == second_exit
    assert first_output == second_output
