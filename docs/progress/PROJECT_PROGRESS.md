# Project Progress

## Current State

- Current Phase: Phase 4 — AI Recommendation
- Current Sprint: Sprint 24 — Production Embedding Generation (Task 1-2) — Complete
- Last Completed Task: Sprint 24 / Task 2 — Validation, Update PROJECT_PROGRESS.md
- Last Commit: (recorded after commit; Sprint 24 / Task 2)
- Validation: Established — `ruff check`, `mypy` (strict), `pytest` all passing (199 tests); demo script re-run directly to confirm compatibility with the widened (384-dim) embedding schema

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
- Commit: 465ba5d
- Notes: PostgreSQL itself was already approved (ADR-001); `psycopg` (v3, binary distribution — no compiler/libpq-dev needed, important since this sandbox has no passwordless sudo for system packages) was chosen as the specific driver, an implementation-level choice analogous to Sprint 7's stdlib-vs-requests decision, not a new architectural decision.

### Task 2 — Database Schema

- Status: Done
- Summary: Added `migrations/0001_create_books_table.sql` (repo root, sibling to `src`/`tests`): `books` table with `id UUID PRIMARY KEY`, `isbn TEXT NOT NULL UNIQUE`, `title`/`author`/`category TEXT NOT NULL` — matching Task 1's adapter columns exactly.
- Validation: Started a disposable `postgres:16-alpine` container via plain `docker run` (ad hoc, not yet the automated Task 3 suite), applied the migration via `psql`, confirmed via `\d books` that the table/constraints match the intended schema (PK on `id`, UNIQUE on `isbn`). Then ran an end-to-end smoke script against that same instance exercising `PostgreSQLBookRepository` (add, get_by_id, get_by_isbn, update, duplicate-ISBN rejection, remove, remove-missing) — all passed. Container stopped and removed afterward.
- Commit: 5513614
- Notes: No migration-runner tool (e.g. Alembic) introduced — a single checked-in SQL file is the smallest complete change for the first migration; not wired into the Docker image yet since there is no migration-running entrypoint in production (consistent with Sprint 6's placeholder-CMD approach). `migrations/` is not copied into the Docker image (`.dockerignore` predates this file and doesn't need to change, since it isn't referenced by any runtime code path yet).

### Task 3 — Repository Validation

- Status: Done
- Summary: Added `tests/infrastructure/test_postgresql_book_repository.py`, mirroring `test_in_memory_book_repository.py`'s exact scenarios (add/get_by_id/get_by_isbn/update/remove/duplicate ISBN, both in-batch and update-conflict) against `PostgreSQLBookRepository`, run against a `testcontainers` `PostgresContainer("postgres:16-alpine")` — a disposable instance started once per test module, with `migrations/0001_create_books_table.sql` applied on startup and `TRUNCATE TABLE books` between tests for isolation, then torn down automatically at module end. Added `[[tool.mypy.overrides]] module = "testcontainers.*"` to `pyproject.toml` since the package ships no type stubs.
- Validation:
  - `python3 -m ruff check src tests` — pass
  - `python3 -m mypy src tests` — pass (32 source files)
  - `python3 -m pytest -q` — pass (58 passed, ~14s; includes the 11 new Postgres integration tests spinning up/tearing down a real disposable container)
  - Confirmed no leftover containers after the run (`docker ps -a`) — only a pre-existing, unrelated container from outside this session remained.
- Commit: ffceed4
- Notes: Since GitHub-hosted Actions runners provide Docker by default, the Sprint 6 CI workflow (`pytest -q`) will run these integration tests automatically with no workflow changes needed — confirmed by inspection, not by an actual GitHub run.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Sprint 9 complete and back-filled Sprint 9 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 10 — Production Import Workflow

### Task 1 — Import Configuration

- Status: Done
- Summary: Added `src/readmatch_ai/config.py` with `BookRepositoryConfig.from_env()`, reading `BOOK_REPOSITORY_BACKEND` (`in_memory` default, or `postgresql`) and `DATABASE_URL`. Updated `ApplicationContext.create()`'s default path (used only when no explicit `book_repository` is passed — the existing override parameter is untouched) to call a new `_build_book_repository()` that composes `InMemoryBookRepository` or `PostgreSQLBookRepository` based on this config. `application/` package (use cases, mapper) was not touched.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Smoke checks: (1) no env set → still defaults to `InMemoryBookRepository` (backward compatible with Sprint 5 behavior); (2) unknown backend value raises `UnknownBookRepositoryBackendError`; (3) `postgresql` backend without `DATABASE_URL` raises `DatabaseUrlMissingError`; (4) `postgresql` backend with `DATABASE_URL` pointed at a disposable `docker run postgres:16-alpine` (migration applied) correctly composed a real `PostgreSQLBookRepository`. Full `ruff check src tests` / `mypy src tests` / `pytest -q` re-run: 58 passed, no regressions.
- Commit: 74e5602
- Notes: Config module only parses/validates env vars — it does not import any Infrastructure adapter, so `application_context.py` remains the sole place that references concrete adapters (both `InMemoryBookRepository` and now `PostgreSQLBookRepository`), consistent with Sprint 5.

### Task 2 — Production Import Runtime

- Status: Done
- Summary: Added `scripts/import_books.py` (the `scripts/` directory created empty in Sprint 1, now used for the first time). `main(argv, *, book_data_source=None, application_context=None)` parses `--start-date`/`--end-date`, defaults to `ApplicationContext.create()` (Task 1's config-driven wiring) and `Data4LibraryBookDataSource()`, and orchestrates `ImportBooksUseCase` (unchanged, from Sprint 8) against them. The `book_data_source`/`application_context` parameters mirror the existing optional-override pattern already used by `ApplicationContext.create(book_repository=...)` (Sprint 5), enabling Task 3 to exercise the real script without hitting the real API or requiring a specific backend to be pre-configured via env vars.
- Validation: `ruff check` (pass), `mypy` (pass, strict); interactive smoke check ran `main()` end-to-end with an injected fake `BookDataSource` and an `InMemoryBookRepository`-backed `ApplicationContext` (no real network/DB), confirming the imported book was retrievable afterward via `context.get_book_by_isbn_use_case`. Full PostgreSQL-backed end-to-end validation is Task 3.
- Commit: 9cef66c
- Notes: `ImportBooksUseCase`, `Book`, `BookRepository`, etc. (Application/Domain) were not modified — all adapter selection/wiring for this workflow lives in this script, per Task instruction ("keep orchestration outside the Application layer").

### Task 3 — Runtime Validation

- Status: Done
- Summary: Added `tests/test_import_books_runtime.py`, loading `scripts/import_books.py` via `importlib` (it's a script, not an importable package) and exercising its real `main()` against a `testcontainers` disposable `postgres:16-alpine` instance (migration applied) with a `FakeBookDataSource` (no real API calls). Covers: import → retrievable via `context.get_book_by_isbn_use_case` and `get_book_by_id_use_case` → also retrievable via a *second, independently constructed* `PostgreSQLBookRepository` against the same database (proves real persistence, not just in-process object identity); and duplicate entries within a batch don't fail the run.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (35 source files)
  - `python3 -m pytest -q` — pass (60 passed, ~20s; includes 2 new end-to-end tests spinning up/tearing down a real disposable Postgres container each)
  - Confirmed no leftover containers after the run.
- Commit: 12c95fb
- Notes: This completes Phase 1 — Data Foundation per the Sprint goal.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Phase 1 — Data Foundation complete (Sprints 7-10) and Sprint 10 complete; back-filled Sprint 10 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 11 — Popularity Data Foundation

**Sprint Goal adjusted mid-sprint** (user instruction, before any Task 1-4 commit): originally "Popularity Recommendation" (RecommendationEngine port + PopularityRecommendationEngine adapter), narrowed to "Popularity Data Foundation" — persisting `loan_count` as a standalone, provenance-tracked signal. `RecommendationEngine`/`RecommendationQuery`/`RecommendationResult`/`Recommendation`/`RecommendationItem` and the `PopularityRecommendationEngine` adapter are explicitly deferred to a future Sprint. Constraints: no live `BookDataSource` calls at recommendation time (moot now — no recommendation engine this Sprint); `Book`/`BookRepository` unchanged; no PostgreSQL persistence for popularity this Sprint.

### Task 1 — Popularity Domain Model

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book_popularity.py`: `BookPopularity` (`book_id`, `loan_count`, `period_start`, `period_end` — the last two are minimal provenance tracking which query period the signal was observed under, matching `PopularLoanBooksQuery`'s date format) and `BookPopularityRepository` port (`record` upsert, `top_by_loan_count(limit)`).
- Validation: `ruff check` (pass), `mypy` (pass); confirmed the port is abstract and the value object constructs/reads correctly.
- Commit: 0b196bf
- Notes: An earlier draft of this Task also added `domain/recommendation.py` (`Recommendation`/`RecommendationItem`) per the original Task 1 wording, but that was removed (uncommitted) once the Sprint Goal was narrowed — those types have no consumer this Sprint (the engine that would produce/consume them is deferred) and would be dead code. `Book`/`BookRepository` not modified.

### Task 2 — InMemory Popularity Repository

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/in_memory_book_popularity_repository.py`: `InMemoryBookPopularityRepository(BookPopularityRepository)`, dict-keyed by `BookId` (upsert semantics via `record`), `top_by_loan_count` sorts descending and slices to `limit`.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed ranking order, limit truncation, and upsert-overwrite behavior.
- Commit: 9e4f34b
- Notes: No PostgreSQL adapter added — explicitly out of scope for this Sprint per user instruction.

### Task 3 — Import Wiring for Popularity

- Status: Done
- Summary: `ImportBooksUseCase` constructor now also takes `book_popularity_repository: BookPopularityRepository`; for each successfully imported book, records `BookPopularity(book_id, loan_count=source_book.loan_count, period_start=query.start_date, period_end=query.end_date)` — reuses `loan_count` already present in the in-hand `PopularLoanBook`/`PopularLoanBooksQuery`, no extra `BookDataSource` call (per user's explicit "no live call at recommendation time" constraint — moot for the engine, but this confirms the import path was already call-free too). `scripts/import_books.py` wires `InMemoryBookPopularityRepository` by default (overridable, mirroring existing optional-param pattern). Fixed Sprint 8's `tests/application/test_import_books_use_case.py` (constructor signature change) to keep the suite green.
- Validation: `ruff check src tests scripts` (pass), `mypy src tests scripts` (pass, 37 source files), `pytest -q` (pass, 60 passed — Sprint 8 regressions fixed). Interactive smoke check confirmed the script records `BookPopularity` with correct `loan_count` and period provenance end-to-end.
- Commit: dc091e6
- Notes: Because there is still no PostgreSQL adapter for `BookPopularityRepository`, and the script constructs a fresh `InMemoryBookPopularityRepository()` per run when not injected, popularity data does not currently persist across process runs in production use — a known, explicitly in-scope-excluded gap (PostgreSQL persistence deferred, per user instruction) to address in a future Sprint alongside `PopularityRecommendationEngine`.

### Task 4 — Validation

- Status: Done
- Summary: Added `tests/domain/test_book_popularity.py` (port is abstract), `tests/infrastructure/test_in_memory_book_popularity_repository.py` (ranking order, limit truncation, empty case, upsert-by-book_id), and extended `tests/application/test_import_books_use_case.py` with `test_successful_import_records_popularity_with_provenance` and `test_duplicate_isbn_does_not_record_popularity`. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 11 completion (adjusted goal) and back-filled Task 1-3 commit hashes.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (39 source files)
  - `python3 -m pytest -q` — pass (67 passed, up from 60; 7 new tests)
  - Confirmed no leftover Docker containers after the run.
- Commit: (recorded after commit)
- Notes: No contract tests for `RecommendationEngine` (as originally listed in the Sprint brief) since that port was deferred along with the engine per the mid-sprint Goal adjustment — validation here covers what was actually built (`BookPopularityRepository` + import wiring).

## Sprint 12 — Popularity Persistence & Repeated Import Correction

### Task 1 — Repeated Import Behavior

- Status: Done
- Summary: Fixed `ImportBooksUseCase.execute()`: when `DuplicateISBNError` is raised, it now looks up the existing Book via `book_repository.get_by_isbn` and records/refreshes its popularity against that Book's real identity (instead of silently doing nothing, as Sprint 11 had it). Extracted `_record_popularity` to avoid duplicating the `BookPopularity` construction between the new-book and existing-book paths. No duplicate `Book` is ever created — the existing identity is reused, `add()` still fails/is caught exactly as before.
- Validation: `ruff check src tests scripts` (pass), `mypy src tests scripts` (pass, 39 source files). Interactive smoke check: import a book, then re-import the same ISBN in a later "period" with a different `loan_count` — confirmed exactly one `BookPopularity` record exists, referencing the *original* `BookId`, with the *refreshed* `loan_count`/period, and no second `Book` was created. Updated Sprint 11's `test_duplicate_isbn_does_not_record_popularity` (renamed/rewritten — its old assertion happened to still pass numerically but its stated intent was now wrong) and added `test_reimporting_existing_book_refreshes_popularity_without_duplicate_book`. Full suite: `pytest -q` — 68 passed.
- Commit: 0fb004e
- Notes: This corrects a behavior explicitly identified as wrong in Sprint 11's own design (that Sprint recorded no popularity at all for duplicates) — the Sprint 12 brief called this out directly ("Do not suppress a valid popularity update merely because the Book already exists").

### Task 2 — PostgreSQL Popularity Schema

- Status: Done
- Summary: Added `migrations/0002_create_book_popularity_table.sql`: `book_popularity(book_id UUID PRIMARY KEY REFERENCES books(id), loan_count INTEGER NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL)` plus `idx_book_popularity_loan_count ON book_popularity (loan_count DESC)` for ranking queries. `PRIMARY KEY(book_id)` (not a composite/history key) intentionally matches `InMemoryBookPopularityRepository`'s overwrite-latest-signal semantics — "repeated collection periods" are handled as an upsert-refresh of the single current signal per book, consistent with Task 1's corrected behavior, not an append-only history log.
- Validation: Started a disposable `postgres:16-alpine` container, applied migrations `0001` then `0002` in order, confirmed via `\d book_popularity` that the PK/FK/index all match intent. Verified the FK constraint rejects a `book_popularity` row referencing a non-existent `book_id` (`ForeignKeyViolation`). Container stopped and removed afterward.
- Commit: ffaba15
- Notes: `period_start`/`period_end` kept as `TEXT` (not `DATE`), matching the Domain's `str` representation and avoiding adapter-side type-casting complexity not otherwise needed.

### Task 3 — PostgreSQLBookPopularityRepository

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/postgresql_book_popularity_repository.py`: `PostgreSQLBookPopularityRepository(BookPopularityRepository)`. `record()` uses `INSERT ... ON CONFLICT (book_id) DO UPDATE` (atomic upsert, avoids a check-then-write race). `top_by_loan_count()` uses `ORDER BY loan_count DESC LIMIT`. Any `psycopg.Error` during `record()` is caught, the connection rolled back, and re-raised as a new `BookPopularityPersistenceError` (defined in this module) — callers never see a raw psycopg exception, per "keep database-specific exceptions inside Infrastructure". `InMemoryBookPopularityRepository` was not touched.
- Validation: `ruff check` (pass), `mypy` (pass, strict). End-to-end smoke test against a disposable `postgres:16-alpine` instance (migrations 0001+0002 applied): initial record, upsert-refresh on repeated period, ranking with `limit`, and a deliberate FK violation (popularity for a non-existent `book_id`) correctly raised `BookPopularityPersistenceError` instead of a raw `psycopg` exception. Container stopped/removed afterward. Full `ruff check`/`mypy` re-run: 40 source files, clean.
- Commit: a7472f8
- Notes: Automated pytest integration tests (via `testcontainers`) are Task 4's responsibility — this Task's Postgres validation was manual/ad hoc, matching the Task 1/Task 2 pattern established in Sprint 9.

### Task 4 — Validation and Progress

- Status: Done
- Summary:
  - Added `tests/infrastructure/test_postgresql_book_popularity_repository.py`: record + top_by_loan_count, ranking order, limit truncation, repeated-period upsert (same book_id), and a full `ImportBooksUseCase` end-to-end test with *both* `PostgreSQLBookRepository` and `PostgreSQLBookPopularityRepository` against a disposable `testcontainers` instance (migrations 0001+0002 applied) — confirms repeated import refreshes popularity via the existing Book identity and that no duplicate `books` row is created (verified with a direct `COUNT(*)` query).
  - Extended `ApplicationContext`: added `book_popularity_repository` field and a matching `book_popularity_repository` override param on `create()`; new `_build_book_popularity_repository()` resolves it independently via the same `BookRepositoryConfig.from_env()` used for `book_repository` (InMemory by default, PostgreSQL when `BOOK_REPOSITORY_BACKEND=postgresql`).
  - Updated `scripts/import_books.py` to default `popularity_repository` to `context.book_popularity_repository` instead of always constructing a fresh `InMemoryBookPopularityRepository()` — so a `postgresql`-configured run now persists popularity durably.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (41 source files)
  - `python3 -m pytest -q` — pass (73 passed, up from 68; 5 new integration tests)
  - Confirmed no leftover Docker containers after the run.
  - Separately verified end-to-end with `BOOK_REPOSITORY_BACKEND=postgresql`/`DATABASE_URL` against a disposable instance: `ApplicationContext.create()` produced `isinstance(..., PostgreSQLBookRepository)` **and** `isinstance(..., PostgreSQLBookPopularityRepository)` — satisfies "PostgreSQL imports use PostgreSQLBookPopularityRepository".
- Commit: (recorded after commit)
- Notes: `book_repository` and `book_popularity_repository` still resolve via two independent `psycopg.connect()` calls when both default under the `postgresql` backend (not a shared connection) — correct but slightly wasteful; not addressed here as it wasn't requested and doesn't affect correctness.

## Sprint 13 — Popularity Recommendation Engine

### Task 1 — Recommendation Domain

- Status: Done
- Summary: Added `src/readmatch_ai/domain/recommendation.py`: `RecommendationItem` (`book: Book`, `score`, `source`), `Recommendation` (`items: list[RecommendationItem]`), `RecommendationQuery` (`limit: int`), `RecommendationResult` (`recommendation: Recommendation`). `RecommendationItem` holds the full `Book` (not just `BookId`) so a `RecommendationResult` is self-contained/"complete", matching Task 3's explicit "join popularity data with BookRepository to produce complete recommendation results" — this differs from the earlier Sprint 11 draft (which held just `book_id`) since Sprint 11's version was written before the join requirement was specified.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed construction and field access.
- Commit: 49d5004
- Notes: `RecommendationQuery` intentionally has only `limit` — no personalization fields, since Popularity is non-personalized (ADR-004: cold-start fallback). Wider query fields can be added later without breaking this port if a personalized engine needs them.

### Task 2 — RecommendationEngine Port

- Status: Done
- Summary: Added `src/readmatch_ai/domain/recommendation_engine.py`: `RecommendationEngine` (ABC) with a single `recommend(query: RecommendationQuery) -> RecommendationResult` method. No algorithm-specific detail in the interface.
- Validation: `ruff check` (pass), `mypy` (pass); confirmed the port is abstract.
- Commit: 5c80a61
- Notes: Mirrors the existing `BookRepository`/`BookDataSource`/`BookPopularityRepository` port pattern (ABC + closely-related I/O types co-located in Domain).

### Task 3 — PopularityRecommendationEngine

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/popularity_recommendation_engine.py`: `PopularityRecommendationEngine(RecommendationEngine)`. `recommend()` calls `BookPopularityRepository.top_by_loan_count(query.limit)`, then joins each result with `BookRepository.get_by_id` to build a `RecommendationItem(book, score=loan_count, source="popularity")`. Reads only already-persisted data (`BookPopularityRepository`, `BookRepository`) — no `BookDataSource` import, no external API call, per Task instruction and Sprint 11/12's established "no live call at recommendation time" direction.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check with `InMemoryBookPopularityRepository`/`InMemoryBookRepository` confirmed correct descending ranking, `source`/`score` fields, and that an orphaned `BookPopularity` entry (no matching `Book`) is silently skipped rather than raising. Formal contract/behavior test suite is Task 4.
- Commit: be0a3b7
- Notes: Not wired into `ApplicationContext` this Sprint — not requested by the Task list (unlike Sprint 12 Task 4, which explicitly asked for runtime composition changes); the engine is available for direct construction/tests and future wiring once an API/consumer needs it.

### Task 4 — Validation and Progress

- Status: Done
- Summary: Added `tests/domain/test_recommendation_engine.py` (port is abstract) and `tests/infrastructure/test_popularity_recommendation_engine.py` covering all four required scenarios: ranking (descending by loan_count, correct `score`/`source`), limit handling (truncates to `query.limit`), empty results (no popularity data → empty `Recommendation.items`), and missing Book records (an orphaned `BookPopularity` entry is silently skipped, not raised). Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 13 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (46 source files)
  - `python3 -m pytest -q` — pass (78 passed, up from 73; 5 new tests)
- Commit: (recorded after commit)
- Notes: —

## Sprint 14 — Recommendation Application Integration

### Task 1 — Recommendation UseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/get_recommendations_use_case.py`: `GetRecommendationsUseCase(recommendation_engine: RecommendationEngine)`, `execute(limit: int) -> RecommendationResult`. Constructs `RecommendationQuery` internally from the primitive `limit`, matching the existing primitive-in/domain-type-internally pattern used by `GetBookByIdUseCase`/`GetBookByISBNUseCase`.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check with `PopularityRecommendationEngine` over `InMemoryBookRepository`/`InMemoryBookPopularityRepository` confirmed correct delegation and result.
- Commit: 5041dd2
- Notes: Depends only on the `RecommendationEngine` port (Domain), not `PopularityRecommendationEngine` directly — Hexagonal dependency direction preserved.

### Task 2 — Application Composition

- Status: Done
- Summary: Extended `ApplicationContext`: added `get_recommendations_use_case` field and a `recommendation_engine: RecommendationEngine | None = None` override param on `create()`. Default: `PopularityRecommendationEngine` built from the already-resolved `book_popularity_repository`/`book_repository` (no new backend-selection logic needed — only one `RecommendationEngine` implementation exists). `PopularityRecommendationEngine` is now imported only in `application_context.py`, same as the other concrete adapters — dependency direction unchanged (Domain/Application still see only the `RecommendationEngine` port).
- Validation: `ruff check` (pass), `mypy` (pass, strict); interactive smoke check confirmed the default engine is a `PopularityRecommendationEngine` and that `register_book_use_case` → `book_popularity_repository.record` → `get_recommendations_use_case.execute` reflects persisted state end-to-end. Full `ruff check`/`mypy`/`pytest -q` re-run: 78 passed, no regressions.
- Commit: c989337
- Notes: `recommendation_engine` is not config-driven (unlike the two repositories) since there is currently only one implementation; this can gain backend selection later once a second engine (e.g. Semantic) exists.

### Task 3 — Application Validation

- Status: Done
- Summary: Added `tests/application/test_get_recommendations_use_case.py` with a mocked `FakeRecommendationEngine` (per Task instruction): confirms `limit` is passed through as `RecommendationQuery`, the engine's result is returned unchanged, and an empty-recommendation result flows through correctly. Extended `tests/test_application_context.py`: `test_recommendations_reflect_persisted_popularity` (end-to-end through the default composition) and `test_create_accepts_an_explicit_recommendation_engine` (override param, mirroring the existing `book_repository`/`book_popularity_repository` override tests).
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (48 source files)
  - `python3 -m pytest -q` — pass (83 passed, up from 78; 5 new tests)
- Commit: 2cc6f83
- Notes: Considered asserting `isinstance(..., PopularityRecommendationEngine)` directly on the default-composed context, but that requires reaching into `GetRecommendationsUseCase`'s private attribute (no public field exposes the engine); the behavioral test (`test_recommendations_reflect_persisted_popularity`) already proves the correct engine is wired, so the private-attribute check was dropped as fragile and redundant.

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Sprint 14 complete and back-filled Sprint 14 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 15 — Semantic Embedding Foundation

### Task 1 — Embedding Domain

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book_embedding.py`: `BookEmbedding` (`book_id`, `vector: tuple[float, ...]`, `model_name`, `dimensions`), kept separate from `Book` (mirrors `BookPopularity`'s separation rationale — model/version varies independently of catalog metadata). `__post_init__` validates: `model_name` non-empty, `dimensions` positive, `len(vector) == dimensions`. `vector` uses `tuple` (not `list`) so the frozen dataclass is genuinely immutable/hashable.
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed construction and all three invariant violations raise `ValueError` with clear messages.
- Commit: 667fcba
- Notes: `Book` entity itself was not modified.

### Task 2 — Embedding Ports

- Status: Done
- Summary: Added `src/readmatch_ai/domain/book_embedding_repository.py` (`BookEmbeddingRepository` ABC: `save`, `get_by_book_id`) and `src/readmatch_ai/domain/book_embedding_generator.py` (`BookEmbeddingGenerator` ABC: `generate(book: Book) -> BookEmbedding`). Split into two files (persistence vs. generation are different responsibilities), mirroring `book.py`/`book_repository.py`'s separation rather than co-locating everything in `book_embedding.py`.
- Validation: `ruff check` (pass), `mypy` (pass); confirmed both ports are abstract.
- Commit: 2cda65e
- Notes: Neither port references a specific algorithm/model — `BookEmbeddingRepository` is storage-only (works for any model since `BookEmbedding` itself carries `model_name`/`dimensions`), and `BookEmbeddingGenerator.generate` takes a plain `Book`, so a real ML-based implementation (deferred to Sprint 16, "Embedding Generation Pipeline") can satisfy the same contract as this Sprint's deterministic fake.

### Task 3 — InMemory Embedding Adapters

- Status: Done
- Summary: Added `infrastructure/in_memory_book_embedding_repository.py` (`InMemoryBookEmbeddingRepository`, dict-backed, upsert-by-`book_id`) and `infrastructure/deterministic_fake_book_embedding_generator.py` (`DeterministicFakeBookEmbeddingGenerator`, derives an 8-dimension vector from a SHA-256 digest of `title|author|category` — no ML dependency, no randomness).
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed: same Book → same vector every time (determinism), two different Books → different vectors, `len(vector) == dimensions`, and repository save/get/upsert behavior.
- Commit: d7039e3
- Notes: `DeterministicFakeBookEmbeddingGenerator` is explicitly a test/placeholder implementation (per Task naming) — a real model-backed generator is Sprint 16's responsibility, not this one.

### Task 4 — Validation and Progress

- Status: Done
- Summary: Added `tests/domain/test_book_embedding.py` (construction + all 3 invariant violations), `tests/domain/test_book_embedding_repository.py` and `tests/domain/test_book_embedding_generator.py` (both ports abstract), `tests/infrastructure/test_in_memory_book_embedding_repository.py` (get-missing, save+get, upsert), and `tests/infrastructure/test_deterministic_fake_book_embedding_generator.py` (determinism, distinctness across different book text, vector length matches configured `dimensions` and values in `[0,1]`, `book_id`/`model_name` set correctly). Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 15 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (58 source files)
  - `python3 -m pytest -q` — pass (96 passed, up from 83; 13 new tests)
- Commit: (recorded after commit)
- Notes: —

## Sprint 16 — Embedding Generation Pipeline

### Task 1 — Embedding Generation UseCase

- Status: Done
- Summary: Added `src/readmatch_ai/application/generate_book_embedding_use_case.py`: `GenerateBookEmbeddingUseCase(book_repository, book_embedding_generator, book_embedding_repository)`. `execute(book_id: str) -> BookEmbedding | None` resolves the `Book` via `BookRepository.get_by_id` first (needed since `BookEmbeddingGenerator.generate` requires a full `Book`), returns `None` without persisting anything if the book is missing, otherwise generates via `BookEmbeddingGenerator` and persists via `BookEmbeddingRepository.save` (upsert, so a second run for the same book replaces the first).
- Validation: `ruff check` (pass), `mypy` (pass); interactive smoke check confirmed: missing book returns `None` and persists nothing; a real book generates and persists correctly; re-running for the same book replaces the stored embedding without error.
- Commit: 677cbe8
- Notes: `execute` takes a primitive `book_id: str` (not `BookId`), matching the existing `GetBookByIdUseCase` convention.

### Task 2 — Application Composition

- Status: Done
- Summary: Extended `ApplicationContext`: added `book_embedding_repository` field and `generate_book_embedding_use_case`; new override params `book_embedding_repository`/`book_embedding_generator` on `create()`. Defaults: `InMemoryBookEmbeddingRepository()` (no PostgreSQL adapter yet) and `DeterministicFakeBookEmbeddingGenerator()` (per Task instruction — no real model yet). Both concrete adapters are imported only in `application_context.py`, matching the existing pattern.
- Validation: `ruff check` (pass), `mypy` (pass, strict); interactive smoke check confirmed default composition wires `InMemoryBookEmbeddingRepository` and that register → generate → retrieve works end-to-end through the context. Full `ruff check`/`mypy`/`pytest -q` re-run: 96 passed, no regressions.
- Commit: 0d0d144
- Notes: `book_embedding_generator` is not exposed as a separate `ApplicationContext` field (only used internally to build `generate_book_embedding_use_case`), mirroring how `recommendation_engine` (Sprint 14) also wasn't exposed as its own field — only shared repositories get dedicated fields.

### Task 3 — Application Validation

- Status: Done
- Summary: Added `tests/application/test_generate_book_embedding_use_case.py`: generation persists correctly, re-running replaces (not duplicates) the stored embedding, missing Book returns `None`, and missing Book persists nothing. Extended `tests/test_application_context.py` with 3 end-to-end tests via the default composition: default `book_embedding_repository` is `InMemoryBookEmbeddingRepository`, a generated embedding is retrievable through `context.book_embedding_repository`, and a missing book returns `None` through the full context wiring.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (60 source files)
  - `python3 -m pytest -q` — pass (103 passed, up from 96; 7 new tests)
- Commit: 4578643
- Notes: —

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Sprint 16 complete and back-filled Sprint 16 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 17 — Vector Storage Foundation

### Task 1 — PostgreSQL Embedding Repository

- Status: Done
- Summary: Added `migrations/0003_create_book_embeddings_table.sql` (`book_embeddings(book_id UUID PRIMARY KEY REFERENCES books(id), vector DOUBLE PRECISION[] NOT NULL, model_name TEXT NOT NULL, dimensions INTEGER NOT NULL)` — a plain PostgreSQL array column, no pgvector extension yet per this Sprint's explicit deferral to Sprint 18) and `src/readmatch_ai/infrastructure/postgresql_book_embedding_repository.py`: `PostgreSQLBookEmbeddingRepository(BookEmbeddingRepository)`. `save()` uses `INSERT ... ON CONFLICT (book_id) DO UPDATE` (atomic upsert, PK-by-book_id matches `InMemoryBookEmbeddingRepository`'s overwrite semantics). `psycopg.Error` is caught and translated into a new `BookEmbeddingPersistenceError` (mirrors `BookPopularityPersistenceError` from Sprint 12) so no database-specific exception escapes Infrastructure.
- Validation: `ruff check` (pass), `mypy` (pass, strict). End-to-end smoke test against a disposable `postgres:16-alpine` instance (migrations 0001+0003 applied): missing embedding returns `None`, save+get round-trips correctly, a second save with different vector/model_name/dimensions replaces the first (upsert), and a deliberate FK violation (embedding for a non-existent `book_id`) correctly raised `BookEmbeddingPersistenceError` instead of a raw `psycopg` exception. Container stopped/removed afterward.
- Commit: d7b3d78
- Notes: No separate "Database Schema" Task existed this Sprint (unlike Sprint 9/12) — the migration was added here as a necessary part of implementing a working adapter.

### Task 2 — Application Composition

- Status: Done
- Summary: Added `_build_book_embedding_repository()` to `application_context.py`, following the exact same shape as `_build_book_repository`/`_build_book_popularity_repository`: resolves `PostgreSQLBookEmbeddingRepository` when `BOOK_REPOSITORY_BACKEND=postgresql`, otherwise `InMemoryBookEmbeddingRepository` — preserving InMemory as the default whenever the backend is unset (the config's own default value). The existing `book_embedding_repository` override param on `create()` (added Sprint 16) now defaults to this new resolver instead of unconditionally constructing `InMemoryBookEmbeddingRepository()`.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Confirmed with no env vars set: `ApplicationContext.create().book_embedding_repository` is still `InMemoryBookEmbeddingRepository` (default preserved). Confirmed with `BOOK_REPOSITORY_BACKEND=postgresql`/`DATABASE_URL` against a disposable instance: it resolves to `PostgreSQLBookEmbeddingRepository`, and `generate_book_embedding_use_case` (unmodified `GenerateBookEmbeddingUseCase`) works end-to-end against it — demonstrating the switch requires zero Application-layer changes. Full `ruff check`/`mypy`/`pytest -q` re-run: 103 passed, no regressions.
- Commit: 9524b65
- Notes: `book_embedding_generator` is unaffected by this Task — it remains hardcoded to `DeterministicFakeBookEmbeddingGenerator` regardless of backend (no real generator exists yet; not part of this Sprint's scope).

### Task 3 — Application Validation

- Status: Done
- Summary: Added `tests/infrastructure/test_postgresql_book_embedding_repository.py`, mirroring `test_in_memory_book_embedding_repository.py`'s exact scenario names/structure (get-missing, save+get, upsert) against `PostgreSQLBookEmbeddingRepository`, run via a disposable `testcontainers` `postgres:16-alpine` instance (migrations 0001+0003 applied), demonstrating contract compatibility with the InMemory implementation.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (62 source files)
  - `python3 -m pytest -q` — pass (106 passed, up from 103; 3 new integration tests)
  - Confirmed no leftover Docker containers after the run.
- Commit: c3a4753
- Notes: —

### Task 4 — Update PROJECT_PROGRESS.md

- Status: Done
- Summary: Updated Current State to mark Sprint 17 complete and back-filled Sprint 17 Task 1-3 commit hashes.
- Validation: N/A (documentation-only update)
- Commit: (recorded after commit)
- Notes: —

## Sprint 18 — Semantic Vector Foundation

### Task 1 — pgvector Storage and Similarity Search

- Status: Done
- Summary: Added `migrations/0004_add_pgvector_to_book_embeddings.sql`: `CREATE EXTENSION IF NOT EXISTS vector`, alters `book_embeddings.vector` from `DOUBLE PRECISION[]` to a fixed-width `vector(8)` column (8 matches `DeterministicFakeBookEmbeddingGenerator`'s default dimensions — the only generator wired today; pgvector requires a fixed dimension per column, so a future generator with a different dimension, e.g. Sentence Transformers in Sprint 19, will need its own migration), and adds an `hnsw (vector vector_cosine_ops)` index. Added production dependency `pgvector` (Python package) to `pyproject.toml` for the psycopg type adapter. Extended `BookEmbeddingRepository` (Domain port) with an abstract `find_similar(vector, limit) -> list[BookEmbedding]` method — the similarity-search capability is expressed entirely through the existing port, so the Application layer never sees pgvector/Infrastructure details. Implemented `find_similar` on both adapters: `InMemoryBookEmbeddingRepository` computes cosine similarity in pure Python (skipping any stored embedding whose dimension doesn't match the query vector, rather than raising) so its behavior mirrors the PostgreSQL adapter; `PostgreSQLBookEmbeddingRepository` now calls `register_vector(connection)` in its constructor and orders by pgvector's cosine-distance operator (`vector <=> %s LIMIT %s`). `save`/`get_by_book_id` signatures and upsert semantics are unchanged (existing contract preserved) — only the on-the-wire representation changed from a plain array to a `pgvector.Vector`. No `ApplicationContext` changes were needed: `_build_book_embedding_repository()` already constructs `PostgreSQLBookEmbeddingRepository(connection)` with the same signature, so the pgvector-backed adapter is wired through automatically.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Manual smoke validation against a disposable `pgvector/pgvector:pg16` container (migrations 0001+0003+0004 applied): confirmed `CREATE EXTENSION vector` succeeds, the `DOUBLE PRECISION[] → vector(8)` cast applies cleanly to an existing table, and insert/select round-trips correctly with pgvector's cosine-distance ordering returning the expected nearest-first order. Formal automated test suite is Task 2.
- Commit: (recorded after commit)
- Notes: pgvector stores vector components as single-precision floats (float32), so a value round-tripped through `PostgreSQLBookEmbeddingRepository` may differ slightly from the float64 value that was saved — an inherent characteristic of pgvector, not a bug; documented in the adapter's docstring and accounted for in Task 2's tests via tolerance-based comparison. Docker Hub pulls of `pgvector/pgvector:pg16` succeed in this environment (confirmed) but are noticeably slower than `postgres:16-alpine` (used by every other integration test in this repo) — only the embedding-specific test module was switched to the pgvector image, all other PostgreSQL integration tests are untouched.

### Task 2 — Repository, Integration, and Similarity-Search Validation

- Status: Done
- Summary: Updated `tests/infrastructure/test_postgresql_book_embedding_repository.py`: switched the `testcontainers` fixture from `postgres:16-alpine` to `pgvector/pgvector:pg16` and applies migrations 0001+0003+0004; `_embedding`/`_embedding_with_vector` now produce 8-dimensional vectors (matching the fixed `vector(8)` column — a 1-dimensional vector, as the pre-pgvector test used, is no longer valid against this schema). Existing exact-equality assertions on saved/retrieved embeddings were changed to a `pytest.approx`-based helper (`_assert_embeddings_almost_equal`) to correctly account for pgvector's float32 storage precision (not a weakened assertion — the prior float64 exact-equality assumption no longer holds against real pgvector storage). Added similarity-search tests: empty-repository case, cosine-distance ranking order (closest/middle/farthest), and limit truncation — mirrored on `InMemoryBookEmbeddingRepository` in `tests/infrastructure/test_in_memory_book_embedding_repository.py` (plus a dimension-mismatch-is-skipped case, since only the in-memory adapter can hold mixed-dimension vectors). Added `test_application_context_generates_and_finds_similar_embeddings_via_postgresql`, an end-to-end integration test proving the full path — `ApplicationContext.create()` → `generate_book_embedding_use_case` → real pgvector persistence → `book_embedding_repository.find_similar()` — works through the composition root against a real disposable Postgres instance, confirming "wired through ApplicationContext" without any `ApplicationContext` code changes being necessary. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 18 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (62 source files)
  - `python3 -m pytest -q` — pass (114 passed, up from 106; 8 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 19 — Semantic Recommendation Engine

### Task 1 — Semantic Recommendation Engine and Use Case

- Status: Done
- Summary: Extended `RecommendationQuery` (Domain, `domain/recommendation.py`) with an optional `book_id: BookId | None = None` field — the "appropriate recommendation port" extension named in the Sprint brief, reusing the existing `RecommendationEngine.recommend(query)` contract instead of adding a new/parallel port (Sprint 13's docstring already anticipated "Popularity, Semantic, and ALS engines... all implement this same contract"). Non-personalized engines (Popularity) simply ignore the new field; the default is `None` so no existing call site (`RecommendationQuery(limit=n)`) needed to change. Added `src/readmatch_ai/infrastructure/semantic_recommendation_engine.py`: `SemanticRecommendationEngine(RecommendationEngine)`, constructed from `BookEmbeddingRepository` + `BookRepository` (mirroring `PopularityRecommendationEngine`'s shape). `recommend()`: raises `ValueError` if `query.book_id` is `None` (the engine cannot answer "similar to what?"); returns an empty `Recommendation` if the source book has no stored embedding; otherwise calls `BookEmbeddingRepository.find_similar(source_embedding.vector, limit=query.limit + 1)` (fetching one extra candidate since the source book's own embedding is typically its own closest match), excludes the source `book_id` from the results, joins each remaining candidate with `BookRepository.get_by_id` (skipping an embedding whose Book can no longer be found, same as the Popularity engine's orphan handling), and computes a cosine-similarity `score` per item (`source="semantic"`) — `find_similar` itself returns embeddings only, not scores, so the engine derives the score locally from the two vectors it already holds. Added `src/readmatch_ai/application/generate_semantic_recommendation_use_case.py`: `GenerateSemanticRecommendationUseCase(recommendation_engine: RecommendationEngine)`, `execute(book_id: str, limit: int) -> RecommendationResult` — parses the primitive `book_id` into `BookId` and constructs the `RecommendationQuery`, matching the existing primitive-in/domain-type-internally convention. Wired into `ApplicationContext`: added `generate_semantic_recommendation_use_case` field and a `semantic_recommendation_engine: RecommendationEngine | None = None` override param on `create()`, defaulting to `SemanticRecommendationEngine` built from the already-resolved `book_embedding_repository`/`book_repository` — exactly the same pattern `recommendation_engine`/`PopularityRecommendationEngine` already uses.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Formal test suite is Task 2.
- Commit: (recorded after commit)
- Notes: `find_similar`'s "exclude the source book" requirement is handled by over-fetching by one and filtering, rather than pushing exclusion logic into `BookEmbeddingRepository` itself — keeps the Sprint 18 port unchanged (no port signature change this Sprint) and keeps "exclude self" as Semantic-recommendation-specific policy, not a general repository concern (Popularity has no analogous need to exclude anything).

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/infrastructure/test_semantic_recommendation_engine.py` (InMemory-backed unit tests): ranks by similarity and excludes the source book, respects `limit`, returns empty when the source book has no embedding, skips an embedding whose Book is missing, raises `ValueError` when `RecommendationQuery.book_id` is `None`. Added `tests/application/test_generate_semantic_recommendation_use_case.py` mirroring `test_get_recommendations_use_case.py`'s `FakeRecommendationEngine` pattern: `book_id`/`limit` are correctly passed through as a `RecommendationQuery`, the engine's result is returned unchanged, and an empty result flows through correctly. Extended `tests/test_application_context.py`: `test_semantic_recommendations_reflect_persisted_embeddings` (default composition, end-to-end: register two books, generate both embeddings, confirm the *other* book — not the source — comes back with `source="semantic"`) and `test_create_accepts_an_explicit_semantic_recommendation_engine` (override param, mirroring the existing `recommendation_engine` override test). Extended `tests/infrastructure/test_postgresql_book_embedding_repository.py` with `test_application_context_generates_semantic_recommendations_via_postgresql`, reusing the module's existing `pgvector/pgvector:pg16` testcontainer fixture (no new container/image) to prove the full path — `ApplicationContext.create()` → two real `generate_book_embedding_use_case` calls → `generate_semantic_recommendation_use_case` — works end-to-end against real pgvector-backed Postgres. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 19 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (66 source files)
  - `python3 -m pytest -q` — pass (125 passed, up from 114; 11 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 20 — Hybrid Recommendation Foundation

### Task 1 — Hybrid Recommendation Engine and Use Case

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/hybrid_recommendation_engine.py`: `HybridRecommendationEngine(RecommendationEngine)`, constructed from a popularity engine and a semantic engine (both typed as the `RecommendationEngine` port, so it composes with any implementation, not just the two concrete Sprint 13/19 adapters) plus a `popularity_weight: float = 0.5` (validated to `[0, 1]`; `semantic_weight` is `1 - popularity_weight` — a single interpolation dial, matching the Sprint brief's "weighting *between* popularity and semantic"). `recommend()`: fetches up to `query.limit` candidates from each sub-engine (semantic only if `query.book_id` is set), min-max normalizes each engine's own scores independently to `[0, 1]` (SYSTEM_ARCHITECTURE.md: "Normalize model scores before combining"; a single-item or all-equal-score list normalizes to `1.0`, not division-by-zero), then merges by `book_id` into one item per book whose score is the *full* weighted-sum of both sides (`popularity_weight * normalized_popularity + semantic_weight * normalized_semantic`, each defaulting to `0.0` if the book wasn't a candidate from that engine) — so a book strong in both engines is correctly merged into a single higher-scoring item rather than losing one side's contribution ("merge duplicates while preserving the highest combined score"). Sorts by combined score descending and truncates to `query.limit` (configurable Top-K). Falls back to popularity-only (effective weight `1.0`) whenever semantic has no candidates — no `book_id` given, or the source book has no embedding yet — rather than silently scaling every score down by the configured weight; this directly matches ADR-004 ("Popularity is the baseline and cold-start fallback") rather than inventing new fallback behavior. All merged items carry `source="hybrid"`. Added `src/readmatch_ai/application/generate_hybrid_recommendation_use_case.py`: `GenerateHybridRecommendationUseCase(recommendation_engine: RecommendationEngine)`, `execute(limit: int, book_id: str | None = None) -> RecommendationResult` — `book_id` is optional (unlike Sprint 19's Semantic use case, which requires one), since Hybrid is meaningful with or without a source book. Wired into `ApplicationContext`: added `generate_hybrid_recommendation_use_case` field and a `hybrid_recommendation_engine: RecommendationEngine | None = None` override param on `create()`, defaulting to `HybridRecommendationEngine` built from the *same already-resolved* popularity/semantic engine instances used for `get_recommendations_use_case`/`generate_semantic_recommendation_use_case` — so an explicit override of either of those engines also flows into the default Hybrid engine, keeping composition consistent and avoiding constructing duplicate engine instances. `get_recommendations_use_case`'s default engine is unchanged (still Popularity) — Hybrid is exposed as an additional, separate use case rather than replacing an existing default, consistent with how Semantic was added in Sprint 19.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Formal test suite is Task 2.
- Commit: (recorded after commit)
- Notes: Each sub-engine is queried for exactly `query.limit` candidates (not an over-fetched pool) before merging — the smallest complete implementation satisfying "configurable Top-K"; a book ranked outside the top-`limit` in *both* individual engines cannot surface via the merge even if its combined score would qualify. Documented here as a known MVP simplification (ADR-006 explicitly scopes weighted-normalized-score fusion as the *MVP* hybrid ranker), not addressed since it wasn't requested and the common case (small catalogs, the two engines' top-K sets overlapping) is unaffected.

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/infrastructure/test_hybrid_recommendation_engine.py` (fake popularity/semantic engines, no repositories needed): a book present in both engines' results merges into one item whose score sums both weighted-normalized contributions and outranks single-source items; `limit` is respected; falls back fully to popularity (score `1.0`, semantic engine never even called) when `query.book_id` is `None`; falls back fully to popularity when the semantic engine legitimately returns no candidates (source book has no embedding); both-empty returns an empty result; a higher `popularity_weight` changes the winner between a "popularity favorite" and a "semantic favorite"; constructor rejects a `popularity_weight` outside `[0, 1]`. Added `tests/application/test_generate_hybrid_recommendation_use_case.py` mirroring the Sprint 19 `FakeRecommendationEngine` pattern, including the optional-`book_id`-omitted case. Extended `tests/test_application_context.py`: `test_hybrid_recommendations_combine_popularity_and_semantic_signals` (default composition, end-to-end: register two books, generate both embeddings, record popularity for the *other* book only, confirm it comes back with `source="hybrid"`) and `test_create_accepts_an_explicit_hybrid_recommendation_engine` (override param). Extended `tests/infrastructure/test_postgresql_book_embedding_repository.py` with `test_application_context_generates_hybrid_recommendations_via_postgresql`, reusing the module's existing `pgvector/pgvector:pg16` testcontainer fixture (no new container/image, per Sprint instruction) to prove the full path — real Postgres book/embedding persistence plus `book_popularity_repository.record()` — flows correctly through `generate_hybrid_recommendation_use_case`. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 20 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (70 source files)
  - `python3 -m pytest -q` — pass (140 passed, up from 125; 15 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 21 — Recommendation Evaluation Framework

### Task 1 — Evaluation Domain, Metrics, and Pipeline

- Status: Done
- Summary: Added `src/readmatch_ai/domain/evaluation.py`: `EvaluationCase` (`book_id` + non-empty `relevant_book_ids: frozenset[BookId]`, deliberately decoupled from *how* relevance was derived — category overlap, curated fixtures, or a future user-interaction signal are all equally valid producers, none of which exist as an approved capability yet, so the port only defines the resulting contract), `EvaluationDataset` (non-empty `tuple[EvaluationCase, ...]`), and `EvaluationResult` (per-engine aggregate metrics: `engine_name`, `k`, `precision_at_k`, `recall_at_k`, `map_at_k`, `ndcg_at_k`, `hit_rate_at_k`, `case_count` — comparable across engines since every field is a plain mean). Added `src/readmatch_ai/domain/evaluation_metrics.py`: five pure, dependency-free ranking-metric functions (`precision_at_k`, `recall_at_k`, `average_precision_at_k`, `ndcg_at_k` — binary relevance, standard log2 discount — and `hit_rate_at_k`), each operating on a plain `Sequence[BookId]`/`frozenset[BookId]` so they have no dependency on `RecommendationItem`/engines at all; `k <= 0` raises `ValueError` uniformly. `precision_at_k` divides by `k` (not by however many were actually recommended), matching the standard IR convention of penalizing a short result list rather than scoring it as if `k` were smaller. Added `src/readmatch_ai/application/evaluate_recommendation_engine_use_case.py`: `EvaluateRecommendationEngineUseCase` — unlike every other use case in this codebase, it is *stateless* (no constructor dependencies) and takes the `RecommendationEngine` to evaluate as an `execute()` parameter alongside `engine_name`/`dataset`/`k`, since evaluation's entire purpose is comparing multiple engines against the same dataset (a fixed constructor-injected engine, as `GetRecommendationsUseCase` uses, would work against exactly the wrong shape for this problem). For each `EvaluationCase`, queries the engine once (`RecommendationQuery(limit=k, book_id=case.book_id)` — reusing the same port every other recommendation use case already goes through, so Popularity/Semantic/Hybrid are evaluated identically without any engine-specific code), computes all five metrics against that case's `relevant_book_ids`, then returns the mean of each metric across the dataset as one `EvaluationResult`. Wired into `ApplicationContext`: added `evaluate_recommendation_engine_use_case` field (constructed with no arguments — it's stateless) plus three new fields exposing the already-resolved engine instances directly — `recommendation_engine`, `semantic_recommendation_engine`, `hybrid_recommendation_engine` (previously local-only inside `create()`) — so a caller can hand any of them to the evaluation use case. No repository or Infrastructure adapter is imported by either the Domain evaluation module or the Application use case — the entire pipeline depends only on `RecommendationEngine` (an existing Domain port) and plain Domain value objects, satisfying "without introducing infrastructure coupling" by construction, not by convention.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Formal test suite is Task 2.
- Commit: (recorded after commit)
- Notes: No "ground truth from category" or similar auto-derivation helper was added — inventing a specific relevance-derivation policy (e.g. same-`Category` = relevant) wasn't named in the Sprint brief and would be a scope-expanding architectural choice belonging to the Planning Agent, not an implementation detail. `EvaluationCase.relevant_book_ids` is deliberately a plain field so any future ground-truth source (curated fixtures now; a real user-interaction signal later, if ever approved) can populate it without touching the evaluation pipeline itself.

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/domain/test_evaluation.py` (`EvaluationCase`/`EvaluationDataset` reject empty `relevant_book_ids`/`cases`; construct correctly otherwise). Added `tests/domain/test_evaluation_metrics.py`: all five metrics reject `k <= 0`; `precision_at_k`/`recall_at_k` hand-computed hit-counting including the "divides by k, not by result length" case; `average_precision_at_k`/`ndcg_at_k` verified against an independently hand-computed (and, for NDCG, independently re-derived via `math.log2` in the test itself) multi-hit ranked scenario, plus perfect-ranking (`== 1.0`), no-hits (`== 0.0`), and empty-relevant (`== 0.0`) edge cases; `hit_rate_at_k` confirms a hit within `k` scores `1.0`, a hit beyond `k` is correctly ignored (scores `0.0`). Added `tests/application/test_evaluate_recommendation_engine_use_case.py` (fake engines, deterministic per-case control): confirms each `EvaluationCase` is queried with `limit=k` and the case's `book_id`; confirms dataset-level aggregation is the mean across cases via a hand-picked hit/miss pair (`0.5` for every metric); confirms an all-miss dataset returns all-zero metrics. Extended `tests/test_application_context.py`: `test_create_exposes_the_resolved_recommendation_engines` (the three new fields hold the expected concrete adapter types by default) and `test_evaluate_recommendation_engine_use_case_scores_the_three_wired_engines` — the Sprint's integration test: registers two books, generates both embeddings, records popularity for one, builds a single-case `EvaluationDataset`, then runs the *same* `evaluate_recommendation_engine_use_case` against `context.recommendation_engine`/`semantic_recommendation_engine`/`hybrid_recommendation_engine` in turn and confirms all three independently score a perfect result (this scenario is simple enough that Popularity, Semantic, and Hybrid all correctly recommend the one relevant book). No new Docker container/image was introduced for this Sprint — the integration test runs entirely against the default in-memory `ApplicationContext`, since evaluation logic is engine-agnostic and Sprint 19/20 already validated Postgres/pgvector wiring for the underlying engines themselves. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 21 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (76 source files)
  - `python3 -m pytest -q` — pass (171 passed, up from 140; 31 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 22 — Recommendation API Foundation

### Task 1 — API Layer

- Status: Done
- Summary: Added `src/readmatch_ai/api/` as a new top-level package, sibling to `domain/`/`application/`/`infrastructure/` — a *driving* adapter distinct from Infrastructure's *driven* adapters (SYSTEM_ARCHITECTURE.md's Main Boundaries list "API" and "Infrastructure" separately), and the direct implementation of ADR-009 ("FastAPI serves recommendations"), previously only a placeholder `CMD` in the Sprint 6 Dockerfile. Added production dependencies `fastapi>=0.115`, `pydantic>=2.5`, `uvicorn[standard]>=0.30` to `pyproject.toml`.
  - `api/schemas.py`: `BookResponse`/`RecommendationItemResponse`/`RecommendationResponse` (Pydantic v2 `BaseModel`s) with `from_domain()` classmethods translating `Book`/`RecommendationResult` — the only place Domain objects are converted to API DTOs, so no Domain type is ever serialized directly.
  - `api/dependencies.py`: `get_application_context(request)` reads `request.app.state.application_context` (built once at startup, not per-request — avoids opening a new `psycopg.connect()` on every request when the `postgresql` backend is configured) and is the sole seam tests override via `app.dependency_overrides`.
  - `api/errors.py`: a single `ValueError -> 400 {"detail": ...}` exception handler, since every existing use case (`GetBookByIdUseCase`, `GenerateSemanticRecommendationUseCase`, etc.) already raises plain `ValueError` for malformed input (e.g. a bad UUID) — without this handler FastAPI would surface those as an opaque 500. FastAPI's own request-validation errors (missing/out-of-range query params) already produce a structured 422 with no handler needed.
  - `api/recommendations_router.py`: three `GET` endpoints — `/recommendations/popularity` (wraps `get_recommendations_use_case`), `/recommendations/semantic/{book_id}` (wraps `generate_semantic_recommendation_use_case`; `book_id` is a required path param, matching the use case's own required-book_id contract), `/recommendations/hybrid` (wraps `generate_hybrid_recommendation_use_case`; `book_id` is an *optional* query param, matching that use case's own optional-book_id contract). `limit` is a `Query(gt=0, le=100)` on all three — API-boundary input validation independent of whatever Domain does or doesn't enforce (`RecommendationQuery.limit` itself has no invariant), satisfying "consistent validation... for invalid requests" without touching Domain.
  - `api/main.py`: `create_app()` factory (a fresh `FastAPI` instance per call, so tests get full isolation) with an `asynccontextmanager` `lifespan` that calls `ApplicationContext.create()` exactly once at startup and stores it on `app.state`; registers the router and exception handler. Module-level `app = create_app()` is the real entrypoint (`uvicorn readmatch_ai.api.main:app`).
  - Updated `Dockerfile`'s `CMD` (was an honest placeholder since Sprint 6, explicitly flagged as "pending ADR-009") to `uvicorn readmatch_ai.api.main:app --host 0.0.0.0 --port 8000`, added `EXPOSE 8000`. Updated `docker-compose.yml` to publish `8000:8000`.
  - No endpoint was added for anything beyond the three named use cases (no book CRUD, no health-check route) — not named in the Sprint brief, and adding either would be an unrequested feature per PROJECT_INSTRUCTIONS.md's scope rules. Semantic/hybrid recommendations for a syntactically-valid-but-nonexistent `book_id` return `200 {"items": []}`, not `404` — this mirrors `SemanticRecommendationEngine`'s existing behavior exactly (it already can't distinguish "book doesn't exist" from "book exists but has no embedding yet"); the API deliberately does not add a new existence-check business rule that the underlying use case doesn't itself have.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Manual smoke test against a real `uvicorn` process (not just `TestClient`): started `uvicorn readmatch_ai.api.main:app` on a local port, `curl`'d all three endpoints (empty-state 200s), an invalid `limit=0` (422 with structured detail), a malformed `book_id` (400 `{"detail": "badly formed hexadecimal UUID string"}`), `/openapi.json` (all three paths present), and `/docs` (200, HTML) — then stopped the process. Formal automated test suite is Task 2.
- Commit: (recorded after commit)
- Notes: `httpx2` (not `httpx`) was added as the dev/test dependency — Starlette's `TestClient` (bundled via `fastapi.testclient`) now prefers `httpx2` and emits a `StarletteDeprecationWarning` when only `httpx` is installed; verified via a real test run that installing `httpx2` alongside removes the warning entirely, so it was made the pinned dependency rather than suppressing the warning. `Dockerfile`/`docker-compose.yml` changes were not validated via an actual `docker build`/`up` in this session (the base image was already cached from Sprint 6; the `uvicorn` `CMD` itself was validated identically via the direct local smoke test above) — per Sprint instruction to avoid unnecessary container/image churn.

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/api/conftest.py`: `application_context` fixture (`ApplicationContext.create()`, in-memory) and `client` fixture (a `TestClient` with `get_application_context` overridden to the fixture context, entered via `with` so the app's own lifespan still runs harmlessly in the background). Added `tests/api/test_recommendations_router.py`: happy-path tests for all three endpoints (popularity reflects persisted `loan_count`; semantic reflects persisted embeddings and excludes the source book; hybrid combines both signals and also works with no `book_id`), empty-state responses, `limit` boundary validation (`0` and `101` both 422), and error-path tests (malformed `book_id` -> 400 with a `detail` field; a well-formed-but-unregistered `book_id` -> 200 empty, not 404, per Task 1's documented decision). Added `tests/api/test_openapi_contract.py`: confirms all three paths appear in `/openapi.json`, the `200` response schema for `/recommendations/popularity` references `RecommendationResponse` (and that `RecommendationResponse`/`RecommendationItemResponse`/`BookResponse` are all present in `components.schemas`), and `/docs` serves HTML. Added `tests/api/test_app_lifespan.py`: the one test that does *not* override `get_application_context` — proves `create_app()`'s real `lifespan` (calling the actual default `ApplicationContext.create()`) serves a working request end-to-end, not just the overridden path every other API test exercises. No new Postgres/pgvector testcontainer was introduced for this Sprint: the API layer is fully backend-agnostic through `ApplicationContext` (already proven against real Postgres/pgvector in Sprints 18-21), so an API-level Postgres test would exercise request/response marshaling only, nothing DB-specific — consistent with the Sprint instruction to avoid recreating containers unnecessarily. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 22 completion, and advanced Current Phase to Phase 3 — Service Layer per the Sprint header.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (87 source files)
  - `python3 -m pytest -q` — pass (186 passed, up from 171; 15 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 23 — Recommendation Demo & End-to-End Showcase

### Task 1 — Demo Script and README

- Status: Done
- Summary: Added `scripts/run_demo.py`, following the existing `scripts/import_books.py` convention (`main(argv, *, application_context=None) -> int`, `_parse_args`, `if __name__ == "__main__": sys.exit(main())`) so it can be driven both from the CLI and (with an injected `ApplicationContext`) from tests.
  - `_SEED_BOOKS`: 8 hand-picked, deterministic books across 3 categories (Software Engineering ×3, Science Fiction ×3, History ×2) with varied `loan_count`, so Popularity/Semantic/Hybrid visibly diverge. ISBN-13 check digits are computed programmatically (`_isbn13`), not hand-typed, to guarantee they pass `ISBN`'s existing checksum validation.
  - `seed_demo_dataset(context)`: registers each book, records its popularity, and generates its embedding — reusing `register_book_use_case`/`book_popularity_repository.record`/`generate_book_embedding_use_case` exactly as they're used elsewhere; no new Application-layer code needed.
  - The demo calls the *actual* REST API, not the use cases directly: it builds a real `create_app()` instance, overrides `get_application_context` (the same seam Sprint 22's tests use) to the seeded context, and issues real HTTP requests via `fastapi.testclient.TestClient` — this exercises real routing/Pydantic validation/JSON serialization in-process, satisfying "exercises the ... recommendation APIs end-to-end" literally, without needing a bound network port or an external server (there's also no book-write endpoint to seed an arbitrary external server through, since Sprint 22 only added read endpoints).
  - `_print_recommendation_comparison`: prints Popularity/Semantic/Hybrid results side by side for one spotlight book, so the differences between strategies are visible in one place (not three separate reports).
  - `_build_evaluation_dataset`/`_print_evaluation_report`: defines "relevant" as same-category books — a policy decision made *locally in this script*, not added to the Evaluation domain itself (`EvaluationCase.relevant_book_ids` was deliberately left source-agnostic in Sprint 21 for exactly this reason). Runs `evaluate_recommendation_engine_use_case` against all three of `ApplicationContext`'s exposed engine fields (`recommendation_engine`/`semantic_recommendation_engine`/`hybrid_recommendation_engine`, from Sprint 21) and prints a metrics table — satisfying "integrate offline evaluation results into the demonstration output."
  - The evaluation output explicitly states embeddings are `DeterministicFakeBookEmbeddingGenerator`, a placeholder — not a real ML model — so semantic/hybrid metrics aren't overstated as representative recommendation quality, per PROJECT_INSTRUCTIONS.md ("do not exaggerate features or evaluation results"; "clearly label synthetic data").
  - Added `README.md` (none existed previously): quick start (install/lint/typecheck/test), how to run the demo and the API server (`uvicorn`/`docker compose`), an API reference for all three endpoints with real curl examples and example JSON responses (verified against actual, checksum-valid ISBNs), and pointers to `docs/agent/architecture/ADR.md`/`SYSTEM_ARCHITECTURE.md` and `docs/progress/PROJECT_PROGRESS.md` for deeper documentation. Opens with the same "this is a placeholder embedding model" caveat as the demo output, for the same reason.
- Validation: `ruff check` (pass), `mypy` (pass, strict). Ran `python scripts/run_demo.py` directly and inspected the output by hand: 8 books seeded across 3 categories; Popularity/Semantic/Hybrid sections all populated and visibly different from each other; evaluation table printed with plausible (0-1 range) metrics for all three engines. Formal automated test suite is Task 2.
- Commit: (recorded after commit)
- Notes: Referencing `docs/agent/architecture/ADR.md`/`SYSTEM_ARCHITECTURE.md` from the README points at their canonical (committed, tracked-in-git) location even though both remain deleted in this session's *uncommitted* working tree — a pre-existing, unrelated anomaly first noted in Sprint 1 and left untouched per that standing precedent; the README reflects repository state, not this sandbox's working-tree quirk.

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/test_run_demo.py`, loading `scripts/run_demo.py` via `importlib` (mirroring `tests/test_import_books_runtime.py`'s existing pattern for testing a non-package script). Discovered and fixed a real bug surfaced by this test: `importlib.util.module_from_spec` + `exec_module` alone does not register the module in `sys.modules` before execution, and `run_demo.py`'s module-level `@dataclass` (`_SeedBook`) needs that registration to resolve its own module's globals — omitting `sys.modules[spec.name] = module` before `exec_module` crashed with `AttributeError: 'NoneType' object has no attribute '__dict__'`. Fixed by registering the module first, which is the standard/correct fix for this importlib pattern (not previously hit by `import_books.py`, which has no module-level dataclasses). Tests cover: the full CLI run produces the expected sections (`[Popularity]`/`[Semantic]`/`[Hybrid]`/evaluation table) via `capsys`; the demo's seeded data is actually persisted and retrievable through the `ApplicationContext` (not just printed); the semantic endpoint invoked through the real API returns valid JSON excluding the source book; and the category-based evaluation dataset groups books correctly. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 23 completion.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (89 source files)
  - `python3 -m pytest -q` — pass (190 passed, up from 186; 4 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Sprint 24 — Production Embedding Generation

### Task 1 — SentenceTransformerBookEmbeddingGenerator and Provider Selection

- Status: Done
- Summary: Added `src/readmatch_ai/infrastructure/sentence_transformer_book_embedding_generator.py`: `SentenceTransformerBookEmbeddingGenerator(BookEmbeddingGenerator)`, defaulting to `sentence-transformers/all-MiniLM-L6-v2` (384-dim, small/CPU-friendly, a standard lightweight production choice — matches the "Sentence Transformers Integration" capability named as the expected next step back when Sprint 18 completed). `generate()` builds the same `title|author|category` text as `DeterministicFakeBookEmbeddingGenerator` and encodes it via `model.encode(text, normalize_embeddings=True)`. `dimensions` is always set to `len(vector)` — derived from the actual produced vector, never a separately-reported model property — so a `BookEmbedding`'s declared dimensions can never diverge from its real vector, on top of the existing `BookEmbedding.__post_init__` invariant (Sprint 15) that already rejects any mismatch before persistence; together these satisfy "ensure generated embedding dimensions are validated before persistence" both by construction and by the pre-existing Domain check. `sentence-transformers` (which pulls in `torch` — a multi-gigabyte dependency) is added only as a new `pyproject.toml` optional-dependency group (`embeddings`), not to `dependencies` or `dev` — `DeterministicFakeBookEmbeddingGenerator` remains the default and every automated test uses it or a fake stand-in, so the heavy dependency is never required for development/CI. Because it's optional, both the module's `__init__` (lazy `from sentence_transformers import SentenceTransformer` inside `__init__`, not at module top level) and `application_context.py`'s builder (lazy import inside the function branch that actually needs it) avoid requiring the package to even be installed unless the real provider is actually selected; a `sentence_transformers.*` mypy override (mirroring the existing `testcontainers.*` one) keeps `mypy --strict` passing regardless.
  - Added `EmbeddingGeneratorConfig` to `config.py` (mirroring `BookRepositoryConfig`'s shape): `EMBEDDING_GENERATOR_BACKEND` (`deterministic` default, or `sentence_transformers`) and optional `EMBEDDING_MODEL_NAME`. Unlike `BookRepositoryConfig`, its default is explicitly documented as *not* meant to silently become the real provider in production — the Sprint brief calls for keeping the deterministic generator the default "for tests and local deterministic scenarios," so switching requires an explicit env var, not just deploying to a "postgresql-configured" environment.
  - Wired via a new `_build_book_embedding_generator()` in `application_context.py`, following the exact same shape as `_build_book_repository`/`_build_book_popularity_repository`/`_build_book_embedding_repository`.
  - **Schema consequence (the one non-trivial decision this Sprint required):** pgvector requires one fixed dimension per column. The existing `book_embeddings.vector` column was `vector(8)` (Sprint 18, sized for `DeterministicFakeBookEmbeddingGenerator`'s old default), but no real embedding model produces 8-dimensional vectors — `all-MiniLM-L6-v2` produces 384. Widening the column to fit the real model *without* also changing the deterministic generator's default would have made the (still-default) deterministic generator incompatible with `BOOK_REPOSITORY_BACKEND=postgresql` — a regression of already-passing Sprint 18-21 integration tests. So both were changed together: `DeterministicFakeBookEmbeddingGenerator`'s `_DEFAULT_DIMENSIONS` moved from 8 to 384, and `migrations/0005_widen_book_embeddings_vector_to_384.sql` drops and recreates the `vector` column at `vector(384)` (validated against a disposable `pgvector/pgvector:pg16` container before committing — pgvector has no in-place "widen" cast between two different fixed dimensions, and there's no production data yet to migrate, so drop+recreate is the correct, smallest-complete approach) plus its `hnsw` index. This keeps both providers uniformly storable through the same schema and preserves every existing `BookEmbeddingRepository` method signature/contract unchanged (`save`/`get_by_book_id`/`find_similar` — only the underlying fixed width changed, not the port).
- Validation: `ruff check` (pass), `mypy` (pass, strict). Migration validated directly against a disposable `pgvector/pgvector:pg16` container (`0001`→`0003`→`0004`→`0005` applied in order; confirmed the column's `format_type` is `vector(384)` and the `hnsw` index rebuilds correctly). `sentence-transformers` was installed and its `encode()` API shape (returns a numpy array; `tuple(float(x) for x in vector)` round-trips correctly) was confirmed directly. **Could not validate an actual real-model download/inference in this sandbox**: `huggingface_hub`'s request path to `huggingface.co` consistently failed with `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Missing Authority Key Identifier`, even though a plain `curl` to the same host succeeds — an environment-specific network/TLS restriction, not a code issue. Formal automated test suite (which never depends on a real download, per Sprint instruction) is Task 2.
- Commit: (recorded after commit)
- Notes: The `SSL`/network limitation above means end-to-end correctness of `SentenceTransformerBookEmbeddingGenerator` against the *real* `all-MiniLM-L6-v2` model was not directly observed in this session — only its API usage (documented `SentenceTransformer.encode` contract) and its logic against a faked substitute (Task 2). This should be re-verified in an environment with unrestricted Hugging Face Hub access before relying on it for a real deployment.

### Task 2 — Validation and Progress

- Status: Done
- Summary: Added `tests/infrastructure/test_sentence_transformer_book_embedding_generator.py`: injects a fake `sentence_transformers` module into `sys.modules` (works whether or not the real optional package is installed, since the adapter imports it lazily) to verify vector/dimensions derivation, model-name propagation, and determinism given a fixed fake output — satisfying "integration tests using a deterministic fake provider" without any heavy dependency or network access. Added `tests/test_config.py`: `EmbeddingGeneratorConfig.from_env()` default/explicit-backend/model-name/unknown-backend cases — the "configuration tests for provider selection" the Sprint asked for explicitly. Extended `tests/test_application_context.py`: confirms the default composition still resolves to `DeterministicFakeBookEmbeddingGenerator` (`model_name == "deterministic-fake"`), and — using the same `sys.modules` fake-injection technique plus `EMBEDDING_GENERATOR_BACKEND=sentence_transformers` — confirms `ApplicationContext.create()`'s config-driven wiring actually routes through to a working generator end-to-end (register → generate → correct vector/model_name), proving "configuration-based provider selection through the Composition Root" without needing the real heavy dependency. Updated `tests/infrastructure/test_postgresql_book_embedding_repository.py` to apply migration `0005` and bumped its local `_DIMENSIONS` constant from 8 to 384 (all vectors in that file are built via a shared zero-padding helper keyed off that constant, so no other change was needed — the file's existing repository/find_similar/ApplicationContext-integration tests all continue to pass unchanged against the new column width). Re-ran `scripts/run_demo.py` directly after these changes to confirm the demo (which relies on the default deterministic provider) still works correctly end-to-end at the new dimension. Updated `PROJECT_PROGRESS.md` (this entry) for Sprint 24 completion, and advanced Current Phase to Phase 4 — AI Recommendation per the Sprint header.
- Validation:
  - `python3 -m ruff check src tests scripts` — pass
  - `python3 -m mypy src tests scripts` — pass (92 source files)
  - `python3 -m pytest -q` — pass (199 passed, up from 190; 9 new tests)
  - Confirmed no leftover Docker containers after the run (only pre-existing, unrelated containers from outside this session remained).
- Commit: (recorded after commit)
- Notes: —

## Current Constraints

- Implement only approved Tasks.
- Preserve unrelated working-tree changes.
- Update this file after validated completion.