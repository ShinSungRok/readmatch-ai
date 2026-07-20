# Project Progress

## Current State

- Current Phase: Phase 1 — Data Foundation
- Current Sprint: Sprint 8 — Book Import Pipeline (Task 1-4) — Complete
- Last Completed Task: Sprint 8 / Task 4 — Update PROJECT_PROGRESS.md
- Last Commit: 917e5b3 (Sprint 8 / Task 3; this Task's commit recorded after commit)
- Validation: Established — `ruff check`, `mypy` (strict), `pytest` all passing (47 tests)

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
- Commit: 32379fe
- Notes: Use case depends only on the `BookRepository` port (Domain), not on `InMemoryBookRepository` directly — Hexagonal dependency direction preserved.

### Task 2 — GetBookByIdUseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/get_book_by_id_use_case.py` with `GetBookByIdUseCase.execute(book_id: str) -> Book | None`, parsing the input into `BookId` and delegating to `BookRepository.get_by_id`.
- Validation: `ruff check src/readmatch_ai/application` (pass), `mypy src/readmatch_ai/application` (pass); interactive smoke check confirmed hit and miss cases via `InMemoryBookRepository`. Full Application test suite added in Task 4.
- Commit: d53cb37
- Notes: Accepts a primitive `str` (not `BookId`) so a future API layer can pass a raw path parameter directly; invalid UUID strings raise `ValueError` from `uuid.UUID`, consistent with existing domain validation style.

### Task 3 — GetBookByISBNUseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/get_book_by_isbn_use_case.py` with `GetBookByISBNUseCase.execute(isbn: str) -> Book | None`, parsing the input into `ISBN` (reusing existing checksum validation) and delegating to `BookRepository.get_by_isbn`.
- Validation: `ruff check src/readmatch_ai/application` (pass), `mypy src/readmatch_ai/application` (pass); interactive smoke check confirmed hit and miss cases via `InMemoryBookRepository`. Full Application test suite added in Task 4.
- Commit: 8d2d90a
- Notes: Same primitive-in / domain-VO-out pattern as `GetBookByIdUseCase` for consistency.

### Task 4 — Application Layer Validation

- Status: Done
- Summary: Added `tests/application/` suite: `test_register_book_use_case.py` (persists + returns Book, rejects duplicate ISBN, rejects invalid ISBN), `test_get_book_by_id_use_case.py` (hit/miss), `test_get_book_by_isbn_use_case.py` (hit/miss). Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 4 completion and back-filled Task 1-3 commit hashes.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (21 source files)
  - `python3 -m pytest -q` — pass (32 passed)
- Commit: (recorded after commit)
- Notes: Test/log update combined into one commit per Sprint brief ("Add Application tests. Update PROJECT_PROGRESS.md." listed as a single Task 4).

## Sprint 5 — Composition Root & Dependency Injection (Book)

### Task 1 — ApplicationContext

- Status: Done
- Summary: Added `src/readmatch_ai/application_context.py` defining `ApplicationContext`, a frozen dataclass holding the wired `BookRepository` port and the three Book use cases. Placed at the package root (sibling of `domain/`, `application/`, `infrastructure/`) since a composition root sits above all layers. No wiring logic yet — that is Task 2.
- Validation: `ruff check src/readmatch_ai/application_context.py` (pass), `mypy src/readmatch_ai/application_context.py` (pass).
- Commit: c918e7f
- Notes: Fields typed against `BookRepository` (the port), not `InMemoryBookRepository` — keeps the container itself abstraction-clean; the concrete adapter choice is confined to the Task 2 factory.

### Task 2 — Dependency Injection

- Status: Done
- Summary: Added `ApplicationContext.create(book_repository: BookRepository | None = None)` classmethod. Defaults to `InMemoryBookRepository` (the only adapter available) and injects the same repository instance into all three use cases. Accepts an optional explicit `BookRepository` for tests or future adapters.
- Validation: `ruff check src/readmatch_ai/application_context.py` (pass), `mypy src/readmatch_ai/application_context.py` (pass); interactive smoke check confirmed all three use cases share the same repository instance end-to-end. Dedicated composition tests added in Task 3.
- Commit: 9fcc701
- Notes: `InMemoryBookRepository` is imported only in this module — the one place in the codebase allowed to reference a concrete Infrastructure adapter directly.

### Task 3 — Runtime Validation

- Status: Done
- Summary: Added `tests/test_application_context.py` covering: default wiring resolves to `InMemoryBookRepository`, an explicit repository can be injected, all three use cases operate on the same repository instance end-to-end (register then read-by-id and read-by-isbn), missing-book lookups return `None`, and separate `create()` calls produce independent, non-shared state.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (23 source files)
  - `python3 -m pytest -q` — pass (37 passed)
- Commit: 2450152
- Notes: Placed at `tests/` root (not under `tests/application/`) mirroring `application_context.py`'s package-root placement as the composition root.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State for Sprint 5 completion and back-filled Sprint 5 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 6 — Runtime Foundation & CI

### Task 1 — Docker Runtime Foundation

- Status: Done
- Summary: Added `Dockerfile` (python:3.12-slim, `pip install --no-cache-dir .` for production deps only — dev extras excluded, non-root `appuser`) and `.dockerignore`. No FastAPI/server exists yet (ADR-009 not implemented), so CMD is an honest placeholder (`import readmatch_ai; print(__version__)`) rather than a fabricated service entrypoint.
- Validation: `docker build -t readmatch-ai:foundation-test .` — succeeded; `docker run --rm readmatch-ai:foundation-test` printed `0.1.0`; confirmed process runs as `appuser`, not root. Test image removed after validation.
- Commit: d26b9d3
- Notes: CMD is a placeholder pending Phase 5/Serving (ADR-009); flagged here so it is not mistaken for a real service entrypoint.

### Task 2 — Local Development Environment

- Status: Done
- Summary: Added `docker-compose.yml` with a single `app` service building from the existing `Dockerfile`, mounting `./src` read-only for local iteration. No PostgreSQL, pgvector, or other external services added, per Task instruction.
- Validation: `docker compose config` (valid), `docker compose up --build` — built and ran successfully, printed `0.1.0`, exited 0. Ran `docker compose down --rmi local` to remove the test image/network afterward.
- Commit: d8fbe90
- Notes: No `version:` key (deprecated in current Compose spec). No ports exposed — no service listens yet.

### Task 3 — Continuous Integration

- Status: Done
- Summary: Added `.github/workflows/ci.yml` triggered on every `push` and `pull_request`. Runs `actions/checkout` + `actions/setup-python` (3.12) + `pip install -e ".[dev]"`, then `ruff check src tests`, `mypy src tests`, `pytest -q` — the same commands used locally throughout all prior Sprints. Independent of Docker (Tasks 1-2); runs directly on the GitHub-hosted runner's Python environment for simplicity.
- Validation: YAML parsed successfully via `python3 -c "import yaml; yaml.safe_load(...)"`; the three CI commands (`ruff check src tests`, `mypy src tests`, `pytest -q`) re-run locally and passed (37 tests). Actual GitHub Actions execution cannot be verified in this environment — will run on first push.
- Commit: 1db187a
- Notes: Python version pinned to 3.12 in CI, matching the Dockerfile's base image for consistency.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Phase 0 — Foundation complete (Sprints 1-6) and Sprint 6 complete; back-filled Sprint 6 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: Kept "Current Phase" labeled Phase 0 (marked Complete) rather than pre-declaring Phase 1, consistent with how Sprint numbers have only been advanced once the next Sprint's kickoff explicitly states it.

## Sprint 7 — Data Ingestion Foundation (External Book Data Source)

### Task 1 — Book Data Source Port

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book_data_source.py` with `BookDataSource` (ABC), `PopularLoanBooksQuery` (start/end date request DTO), and `PopularLoanBook` (unvalidated external response DTO). Distinct from `BookRepository`: this port is for fetching metadata from external providers, not persisting our own aggregate.
- Validation: `ruff check` (pass), `mypy` (pass); confirmed the ABC cannot be instantiated directly.
- Commit: 08247e2
- Notes: Provider selected by the user: 도서관 정보나루 (Data4Library) Open API, targeting the 인기대출도서 (popular loan books) endpoint first. `PopularLoanBook` is deliberately unvalidated (no ISBN checksum, etc.) since cleaning/mapping into `Book` is a later import-pipeline task, not this Sprint. National Library of Korea ISBN bibliographic API explicitly deferred to a future Sprint as a separate provider adapter (per user instruction) — not designed for here.

### Task 2 — Library API Client Skeleton

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/data4library_book_data_source.py` implementing `BookDataSource` for the Data4Library `loanItemSrch` endpoint: builds the request URL (authKey/startDt/endDt/format), calls it via stdlib `urllib.request.urlopen` (10s timeout), and parses the JSON response into `PopularLoanBook`. Auth key resolves from an explicit constructor arg or the `DATA4LIBRARY_AUTH_KEY` env var (raises `Data4LibraryAuthKeyMissingError` if neither is present). No mapping into `Book` and no `BookRepository` writes — import pipeline explicitly out of scope.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed missing-key error and correct request URL construction (`authKey`, `startDt`, `endDt` present) — no real network call made (only `_build_request_url` was exercised directly).
- Commit: a6b71dd
- Notes: Used stdlib `urllib` instead of adding a new HTTP client dependency (e.g. `requests`) to avoid introducing new infrastructure beyond what this Task requires; `dependencies` in `pyproject.toml` remains empty. No real key present anywhere in code/tests.

### Task 3 — Contract Validation

- Status: Done
- Summary: Added `tests/domain/test_book_data_source.py` (port is abstract). Added `tests/infrastructure/test_data4library_book_data_source.py`: auth key missing/from-env/explicit, response parsing via a mocked `urlopen` (patches the module-level import, never touches the network), request URL contains `authKey`/`startDt`/`endDt`, and empty-docs handling. `DATA4LIBRARY_AUTH_KEY` controlled per-test via `pytest.MonkeyPatch` (set/deleted), never read from the real environment.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (27 source files)
  - `python3 -m pytest -q` — pass (43 passed)
- Commit: 2d7b484
- Notes: No test calls the real Data4Library API, per Task instruction — `urlopen` is fully mocked in every test that exercises `search_popular_loans`.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to Phase 1 — Data Foundation, marked Sprint 7 complete, back-filled Sprint 7 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 8 — Book Import Pipeline

### Task 1 — Book Import Mapper

- Status: Done
- Summary: Added `src/readmatch_ai/application/book_import_mapper.py` with `map_to_book(source: PopularLoanBook) -> Book`, delegating all validation to the existing `ISBN`/`Title`/`Author`/`Category` value objects (no new validation logic). Discovered `PopularLoanBook` (Sprint 7) had no `category` field, which `Book` requires — added `category: str` to `PopularLoanBook`, and updated `Data4LibraryBookDataSource._parse_response` to populate it from the real API's `class_nm` (KDC classification name) field. Fixed the Sprint 7 adapter test accordingly.
- Validation: `ruff check src tests` (pass), `mypy src tests` (pass, 28 source files), `pytest -q` (pass, 43 passed); interactive smoke check confirmed a valid `PopularLoanBook` maps correctly and an invalid ISBN raises `ValueError` via the existing `ISBN` value object.
- Commit: 6522b54
- Notes: Extending `PopularLoanBook` and its one existing consumer (the Data4Library adapter/test from Sprint 7) was necessary to make the mapping possible at all — not an unrelated refactor, since `category` is a required `Book` field and this Sprint's explicit purpose is that mapping.

### Task 2 — ImportBooksUseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/import_books_use_case.py` with `ImportBooksUseCase` (constructor-injected `BookDataSource` + `BookRepository`) and `ImportBooksResult` (imported books + skipped duplicate ISBNs). `execute(query: PopularLoanBooksQuery)` fetches from the data source, maps each result via `map_to_book`, and persists via `BookRepository.add`, catching `DuplicateISBNError` per-book so one duplicate does not abort the batch. Reused the existing `PopularLoanBooksQuery` as the use case input instead of introducing a redundant DTO.
- Validation: `ruff check src/readmatch_ai/application` (pass), `mypy src/readmatch_ai/application` (pass); interactive smoke check with a fake `BookDataSource` and `InMemoryBookRepository` confirmed: 2 new books imported, 1 in-batch duplicate ISBN correctly skipped and reported. Formal test suite (success/duplicate/empty) added in Task 3.
- Commit: df13846
- Notes: Mapper-raised `ValueError` (invalid external data) is intentionally left unhandled/propagating — not in this Task's named scenarios (success, duplicate ISBN, empty results); data cleaning is a separate future concern per ROADMAP Phase 1.

### Task 3 — Application Validation

- Status: Done
- Summary: Added `tests/application/test_import_books_use_case.py` with a test-only `FakeBookDataSource` (mocked `BookDataSource`, per Task instruction) and `InMemoryBookRepository`. Covers: successful import persists all books; duplicate ISBN within the same batch is skipped, not fatal; duplicate ISBN against a book already in the repository is skipped; empty provider results return an empty `ImportBooksResult`.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (30 source files)
  - `python3 -m pytest -q` — pass (47 passed)
- Commit: 917e5b3
- Notes: No test calls the real Data4Library API — `FakeBookDataSource` is entirely in-memory, consistent with Sprint 7's contract-testing approach.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Sprint 8 complete and back-filled Sprint 8 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 9 — PostgreSQL Repository Adapter

### Task 1 — PostgreSQL Repository Port Integration

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/postgresql_book_repository.py` implementing `PostgreSQLBookRepository(BookRepository)` — add/get_by_id/get_by_isbn/update/remove via parameterized SQL against a `books` table (schema defined in Task 2). Connection is injected via constructor (lifecycle owned by the caller, not the adapter). ISBN uniqueness relies on the database's UNIQUE constraint; `psycopg.errors.UniqueViolation` is caught and translated into the existing `DuplicateISBNError` so Infrastructure exceptions never leak past this adapter. Added production dependency `psycopg[binary]>=3.1` and dev dependency `testcontainers[postgres]` (for Task 3's disposable integration tests) to `pyproject.toml`.
- Validation: `ruff check` (pass), `mypy` (pass, strict); full `ruff check src tests` / `mypy src tests` / `pytest -q` re-run to confirm the new dependency didn't break anything (47 passed, unchanged). No execution against a real database yet — the `books` table doesn't exist until Task 2's migration is applied; full behavioral validation is Task 3.
- Commit: (recorded after commit)
- Notes: PostgreSQL itself was already approved (ADR-001); `psycopg` (v3, binary distribution — no compiler/libpq-dev needed, important since this sandbox has no passwordless sudo for system packages) was chosen as the specific driver, an implementation-level choice analogous to Sprint 7's stdlib-vs-requests decision, not a new architectural decision.

### Task 2 — Database Schema

- Status: Done
- Summary: Added `migrations/0001_create_books_table.sql` (repo root, sibling to `src`/`tests`): `books` table with `id UUID PRIMARY KEY`, `isbn TEXT NOT NULL UNIQUE`, `title`/`author`/`category TEXT NOT NULL` — matching Task 1's adapter columns exactly.
- Validation: Started a disposable `postgres:16-alpine` container via plain `docker run` (ad hoc, not yet the automated Task 3 suite), applied the migration via `psql`, confirmed via `\d books` that the table/constraints match the intended schema (PK on `id`, UNIQUE on `isbn`). Then ran an end-to-end smoke script against that same instance exercising `PostgreSQLBookRepository` (add, get_by_id, get_by_isbn, update, duplicate-ISBN rejection, remove, remove-missing) — all passed. Container stopped and removed afterward.
- Commit: (recorded after commit)
- Notes: No migration-runner tool (e.g. Alembic) introduced — a single checked-in SQL file is the smallest complete change for the first migration; not wired into the Docker image yet since there is no migration-running entrypoint in production (consistent with Sprint 6's placeholder-CMD approach). `migrations/` is not copied into the Docker image (`.dockerignore` predates this file and doesn't need to change, since it isn't referenced by any runtime code path yet).

### Task 3 — Repository Validation

- Status: Done
- Summary: Added `tests/infrastructure/test_postgresql_book_repository.py`, mirroring `test_in_memory_book_repository.py`'s exact scenarios (add/get_by_id/get_by_isbn/update/remove/duplicate ISBN, both in-batch and update-conflict) against `PostgreSQLBookRepository`, run against a `testcontainers` `PostgresContainer("postgres:16-alpine")` — a disposable instance started once per test module, with `migrations/0001_create_books_table.sql` applied on startup and `TRUNCATE TABLE books` between tests for isolation, then torn down automatically at module end. Added `[[tool.mypy.overrides]] module = "testcontainers.*"` to `pyproject.toml` since the package ships no type stubs.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (32 source files)
  - `python3 -m pytest -q` — pass (58 passed, ~14s; includes the 11 new Postgres integration tests spinning up/tearing down a real disposable container)
  - Confirmed no leftover containers after the run (`docker ps -a`) — only a pre-existing, unrelated container from outside this session remained.
- Commit: (recorded after commit)
- Notes: Since GitHub-hosted Actions runners provide Docker by default, the Sprint 6 CI workflow (`pytest -q`) will run these integration tests automatically with no workflow changes needed — confirmed by inspection, not by an actual GitHub run.

## Current Constraints

- Implement only approved Tasks.
- Preserve unrelated working-tree changes.
- Update this file after validated completion.