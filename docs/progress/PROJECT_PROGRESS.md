# Project Progress

## Current State

- Current Phase: Phase 2 — Recommendation Models
- Current Sprint: Sprint 15 — Semantic Embedding Foundation (Task 1-4) — Complete
- Last Completed Task: Sprint 15 / Task 4 — Validation and Progress
- Last Commit: d7039e3 (Sprint 15 / Task 3; this Task's commit recorded after commit)
- Validation: Established — `ruff check`, `mypy` (strict), `pytest` all passing (96 tests)

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
- Commit: (recorded after commit)
- Notes: `execute` takes a primitive `book_id: str` (not `BookId`), matching the existing `GetBookByIdUseCase` convention.

### Task 2 — Application Composition

- Status: Done
- Summary: Extended `ApplicationContext`: added `book_embedding_repository` field and `generate_book_embedding_use_case`; new override params `book_embedding_repository`/`book_embedding_generator` on `create()`. Defaults: `InMemoryBookEmbeddingRepository()` (no PostgreSQL adapter yet) and `DeterministicFakeBookEmbeddingGenerator()` (per Task instruction — no real model yet). Both concrete adapters are imported only in `application_context.py`, matching the existing pattern.
- Validation: `ruff check` (pass), `mypy` (pass, strict); interactive smoke check confirmed default composition wires `InMemoryBookEmbeddingRepository` and that register → generate → retrieve works end-to-end through the context. Full `ruff check`/`mypy`/`pytest -q` re-run: 96 passed, no regressions.
- Commit: (recorded after commit)
- Notes: `book_embedding_generator` is not exposed as a separate `ApplicationContext` field (only used internally to build `generate_book_embedding_use_case`), mirroring how `recommendation_engine` (Sprint 14) also wasn't exposed as its own field — only shared repositories get dedicated fields.

## Current Constraints

- Implement only approved Tasks.
- Preserve unrelated working-tree changes.
- Update this file after validated completion.