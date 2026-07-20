# Project Progress

## Current State

- Current Phase: Phase 0
- Current Sprint: Sprint 2 — Domain Foundation (Task 1-4) — Complete
- Last Completed Task: Sprint 2 / Task 4 — Progress
- Last Commit: 5a0db80 (Sprint 2 / Task 3; this Task's commit recorded after commit)
- Validation: Established — `ruff check`, `mypy` (strict), `pytest` all passing (17 tests)

## Task Log

Use this format:

### Task N — Title

- Status:
- Summary:
- Validation:
- Commit:
- Notes:

## Sprint 1 — Repository Foundation

### Task 1 — Repository Foundation

- Status: Done
- Summary: Created base Python project directories (`src/readmatch_ai/`, `tests/`, `scripts/`) with minimal placeholders.
- Validation: N/A (structure only; tooling not yet configured)
- Commit: 9fc69ce
- Notes: Package name `readmatch_ai` (src layout). Pre-existing unrelated uncommitted deletion of `docs/agent/architecture/*` left untouched.

### Task 2 — Development Tooling

- Status: Done
- Summary: Added `pyproject.toml` with ruff, mypy (strict), and pytest configuration. Dev dependencies installed via `pip3 install --user --break-system-packages -e ".[dev]"` (system venv module unavailable: missing `python3.14-venv`, no sudo access). Added `.gitignore` for build/cache artifacts.
- Validation: `python3 -m ruff check src tests` (pass), `python3 -m mypy src` (pass), `python3 -m pytest -q` (no tests collected — expected, tests added in Task 3)
- Commit: ef3c6ca
- Notes: FastAPI, PostgreSQL, Docker, Next.js intentionally excluded per Task scope.

### Task 3 — Validation

- Status: Done
- Summary: Added minimal smoke test (`tests/test_smoke.py`) so pytest has something to collect, confirming the lint/typecheck/test commands all work end-to-end.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (3 source files)
  - `python3 -m pytest -q` — pass (1 passed)
- Commit: b71f3b4
- Notes: Commands run directly (no Makefile/task-runner introduced — out of Task scope).

### Task 4 — Project Progress

- Status: Done
- Summary: Updated Current State section (Phase, Sprint, Last Completed Task, Last Commit, Validation) and back-filled Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: 8e6a4e7
- Notes: —

## Sprint 2 — Domain Foundation

### Task 1 — Book Domain

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book.py` with `BookId`, `ISBN` (ISBN-10/13 checksum validation), `Title`, `Author`, `Category` value objects, and `Book` entity (identity-based equality via `BookId`).
- Validation: `ruff check src/readmatch_ai/domain` (pass), `mypy src/readmatch_ai/domain` (pass); interactive smoke check confirmed valid/invalid ISBN handling. Unit tests added in Task 3.
- Commit: e02fbcf
- Notes: No persistence/infrastructure added — domain layer only, per Sprint scope.

### Task 2 — Repository Port

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book_repository.py` defining the `BookRepository` port (ABC) with `add`, `get_by_id`, `get_by_isbn`. No adapter/implementation added.
- Validation: `ruff check src/readmatch_ai/domain` (pass), `mypy src/readmatch_ai/domain` (pass); confirmed ABC cannot be instantiated directly. Contract tests added in Task 3.
- Commit: 8ac37e4
- Notes: Method set kept minimal (no `list_all`) to match Task scope; broader query needs deferred to future Sprints.

### Task 3 — Validation

- Status: Done
- Summary: Added `tests/domain/test_book.py` (BookId, ISBN checksum, Title/Author/Category invariants, identity-based equality) and `tests/domain/test_book_repository.py` (ABC not instantiable; contract verified via a test-only `InMemoryBookRepository` fake — not a production adapter).
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (9 source files)
  - `python3 -m pytest -q` — pass (17 passed)
- Commit: 5a0db80
- Notes: One ruff E501 (line too long) found and fixed during validation.

### Task 4 — Progress

- Status: Done
- Summary: Regrouped Task Log by Sprint (Sprint 1 / Sprint 2) to disambiguate repeated Task numbers, updated Current State for Sprint 2 completion, and back-filled Sprint 2 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Current Constraints

- Implement only approved Tasks.
- Preserve unrelated working-tree changes.
- Update this file after validated completion.