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


_validate_runtime = _load_module("validate_runtime")
main = _validate_runtime.main


def test_main_returns_zero_for_a_valid_default_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    assert main([]) == 0


def test_main_prints_the_runtime_configuration_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)

    main([])

    output = capsys.readouterr().out
    assert "mode: development" in output
    assert "book_repository_backend: in_memory" in output
    assert "Configuration valid." in output


def test_main_returns_nonzero_for_an_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")

    assert main([]) == 1


def test_main_prints_every_violation_for_an_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "staging")
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "not-a-backend")

    exit_code = main([])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "unknown_runtime_mode" in output
    assert "unknown_book_repository_backend" in output


def test_main_never_attempts_a_database_connection_when_static_config_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Invalid: production mode with the default, non-persistent in_memory
    # backend (BOOK_REPOSITORY_BACKEND intentionally left unset).
    monkeypatch.setenv("APPLICATION_MODE", "production")
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    def _poisoned_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("psycopg.connect must not be called when static config is invalid")

    monkeypatch.setattr("psycopg.connect", _poisoned_connect)

    exit_code = main([])

    assert exit_code == 1


def test_main_skips_persistence_validation_for_the_in_memory_backend(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)

    def _poisoned_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("psycopg.connect must not be called for the in_memory backend")

    monkeypatch.setattr("psycopg.connect", _poisoned_connect)

    exit_code = main([])

    assert exit_code == 0
    assert "not applicable" in capsys.readouterr().out


def test_main_validates_persistence_and_returns_nonzero_when_postgresql_is_unreachable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://nouser:nopass@localhost:1/nonexistent")

    exit_code = main([])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Configuration valid." in output
    assert "postgresql_unreachable" in output
    assert "nopass" not in output
    assert "nouser" not in output


def test_main_is_deterministic_across_repeated_calls(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)

    first_exit = main([])
    first_output = capsys.readouterr().out
    second_exit = main([])
    second_output = capsys.readouterr().out

    assert first_exit == second_exit
    assert first_output == second_output


def test_main_is_deterministic_for_an_unreachable_postgresql_backend(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://nouser:nopass@localhost:1/nonexistent")

    first_exit = main([])
    first_output = capsys.readouterr().out
    second_exit = main([])
    second_output = capsys.readouterr().out

    assert first_exit == second_exit == 1
    assert first_output == second_output
