# Project Progress

## Current State

- Current Phase: Phase 0
- Current Sprint: Sprint 3 — Infrastructure Adapter (Book) (Task 1-4) — Complete
- Last Completed Task: Sprint 3 / Task 4 — Progress Log
- Last Commit: 424f090 (Sprint 3 / Task 3; this Task's commit recorded after commit)
- Validation: Established — `ruff check`, `mypy` (strict), `pytest` all passing (25 tests)

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

## Sprint 3 — Infrastructure Adapter (Book)

### Task 1 — BookRepository InMemory Adapter

- Status: Done
- Summary: Extended `BookRepository` port with `update`/`remove` (approved via user clarification — see Notes) and added `BookNotFoundError`. Added `src/readmatch_ai/infrastructure/in_memory_book_repository.py` implementing full CRUD (add, get_by_id, get_by_isbn, update, remove), no ISBN uniqueness yet (Task 3). Replaced the Sprint 2 test-only fake `InMemoryBookRepository` in `tests/domain/test_book_repository.py` (now broken by the port extension) with the real adapter; that file now only keeps the domain-level "port is abstract" contract test.
- Validation: `ruff check src tests` (pass), `mypy src tests` (pass, 11 source files), `pytest -q` (pass, 14 passed — down from 17 after removing the now-redundant fake-based tests, to be re-covered by Task 2 against the real adapter). Interactive smoke check confirmed add/get/update/remove and BookNotFoundError on missing update/remove.
- Commit: 9faaef4
- Notes: Port extension (`update`/`remove`) was not explicitly specified in the Sprint brief ("CRUD" implied it); asked the user/Planning Agent to confirm before changing the domain interface, since ADR.md reserves architecture-level decisions to the Planning Agent. Confirmed: extend the port.

### Task 2 — Repository CRUD behavior validation

- Status: Done
- Summary: Added `tests/infrastructure/test_in_memory_book_repository.py` covering all five `BookRepository` operations against the real `InMemoryBookRepository`: add+get_by_id, get_by_id/get_by_isbn miss cases, update (success + missing raises `BookNotFoundError`), remove (success + missing raises `BookNotFoundError`).
- Validation: `ruff check src tests` (pass), `mypy src tests` (pass, 13 source files), `pytest -q` (pass, 22 passed)
- Commit: 866ae47
- Notes: Duplicate-ISBN behavior intentionally not tested here — dedicated to Task 3.

### Task 3 — Duplicate ISBN constraint

- Status: Done
- Summary: Added `DuplicateISBNError` to `book_repository.py` (domain-level, so any future adapter must raise it too). `InMemoryBookRepository.add`/`update` now reject a Book whose ISBN matches another stored Book with a different `BookId`. Added tests: add-duplicate raises, update-to-another-book's-ISBN raises, update keeping own ISBN unchanged succeeds.
- Validation: `ruff check src tests` (pass), `mypy src tests` (pass, 13 source files), `pytest -q` (pass, 25 passed)
- Commit: 424f090
- Notes: Constraint enforced in both `add` and `update` since both can introduce an ISBN collision; `remove`/`get_*` unaffected.

### Task 4 — Progress Log

- Status: Done
- Summary: Updated Current State for Sprint 3 completion and back-filled Sprint 3 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 4 — Application Layer (Book)

### Task 1 — RegisterBookUseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/register_book_use_case.py` with `RegisterBookInput` (primitive DTO) and `RegisterBookUseCase`. Constructs a `Book` from primitives via existing domain value objects and delegates to `BookRepository.add`; duplicate ISBN rejection relies entirely on the existing `DuplicateISBNError` raised by the repository (no new validation added).
- Validation: `ruff check src/readmatch_ai/application` (pass), `mypy src/readmatch_ai/application` (pass); interactive smoke check confirmed successful registration and duplicate-ISBN rejection via `InMemoryBookRepository`. Full Application test suite added in Task 4.
- Commit: (recorded after commit)
- Notes: Use case depends only on the `BookRepository` port (Domain), not on `InMemoryBookRepository` directly — Hexagonal dependency direction preserved.

### Task 2 — GetBookByIdUseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/get_book_by_id_use_case.py` with `GetBookByIdUseCase.execute(book_id: str) -> Book | None`, parsing the input into `BookId` and delegating to `BookRepository.get_by_id`.
- Validation: `ruff check src/readmatch_ai/application` (pass), `mypy src/readmatch_ai/application` (pass); interactive smoke check confirmed hit and miss cases via `InMemoryBookRepository`. Full Application test suite added in Task 4.
- Commit: (recorded after commit)
- Notes: Accepts a primitive `str` (not `BookId`) so a future API layer can pass a raw path parameter directly; invalid UUID strings raise `ValueError` from `uuid.UUID`, consistent with existing domain validation style.

## Current Constraints

- Implement only approved Tasks.
- Preserve unrelated working-tree changes.
- Update this file after validated completion.