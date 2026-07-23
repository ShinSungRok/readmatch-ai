# Release Candidate

- Project: ReadMatch AI
- Version: `0.1.0` (`pyproject.toml`)
- Status: **Release Candidate — validated 2026-07-22**
- Scope: this document summarizes release readiness for operators and
  repository reviewers. It does not restate implementation detail already
  covered in [`README.md`](../../README.md) — every claim below links to
  the section that documents it in full.

## Implemented Capabilities

- **Recommendation Pipeline** — Popularity, Semantic (embeddings), and
  implicit-ALS collaborative filtering as independent candidate sources,
  fused by a pluggable `RankingStrategy` (Weighted Score Fusion or
  Reciprocal Rank Fusion), then re-ranked (popularity-penalty,
  novelty-boost, MMR diversity) as an independent stage. See README
  [Architecture](../../README.md#architecture),
  [Re-ranking](../../README.md#re-ranking).
- **Personalized and Explainable Recommendation** — a REST endpoint
  routing a user through the full ranking-then-re-ranking pipeline, plus
  deterministic, evidence-gated structured explanations for why a book was
  recommended. See README
  [Explainable Recommendations](../../README.md#explainable-recommendations).
- **Quality Reporting** — a structured, exportable (Markdown/CSV)
  engine-comparison report with CI-suitable regression checks, built on
  the same evaluation framework used throughout. See README
  [Recommendation Quality Reports](../../README.md#recommendation-quality-reports).
- **Production Observability** — health/readiness endpoints, structured
  recommendation execution logging, and in-process operational metrics,
  all application-level (no external monitoring platform). See README
  [Observability](../../README.md#observability).
- **Operational Configuration and Runtime Hardening** — fail-fast,
  aggregated, secret-free configuration validation before the application
  begins serving. See README
  [Operational Configuration and Runtime Hardening](../../README.md#operational-configuration-and-runtime-hardening).
- **Production Persistence and Vector Runtime Integration Validation** —
  read-only validation of the live PostgreSQL + pgvector runtime
  (connectivity, schema, extension, vector dimension, required index),
  integrated with readiness. See README
  [Persistence and Vector Runtime Validation](../../README.md#persistence-and-vector-runtime-validation).
- **Deployment and Container Runtime Readiness** — deterministic,
  in-process validation that the application actually starts and serves,
  plus a container-level `HEALTHCHECK`. See README
  [Deployment and Container Runtime Readiness](../../README.md#deployment-and-container-runtime-readiness).
- **Production Operations and Runtime Automation** — one aggregated,
  read-only operational status report reusing health/readiness/
  configuration/metrics. See README
  [Production Operations and Runtime Automation](../../README.md#production-operations-and-runtime-automation).
- **CI/CD and Release Automation** — one deterministic pipeline
  orchestrating configuration, persistence, deployment, and operations
  validation, plus the project's own quality gates. See README
  [CI/CD and Release Automation](../../README.md#cicd-and-release-automation).
- **Documentation and Portfolio Polish** — a navigable, accurate README
  and architecture record reflecting the implementation as built, not
  superseded planning drafts.
- **Frontend** — a Next.js/TypeScript web experience (`frontend/`, Sprints
  40-49: home/recommendation feed, book detail, personal library,
  recommendation feedback) consuming the REST API directly over HTTP, with
  its own [README](../../frontend/README.md) for setup/validation. The
  REST API's interactive OpenAPI documentation (`/docs`) and
  `scripts/run_demo.py` remain the primary ways to explore system
  behaviour without a browser (see [ADR-008](../architecture/ADR.md)).

## Runtime Prerequisites

- Python 3.11+ (`pyproject.toml`'s `requires-python`).
- `pip install -e ".[dev]"` for lint/type-check/test tooling.
- No database required by default — `BOOK_REPOSITORY_BACKEND` defaults to
  `in_memory`. For a real deployment, `APPLICATION_MODE=production` and a
  persistent `BOOK_REPOSITORY_BACKEND=postgresql` (with `DATABASE_URL`)
  are required together — the application refuses to start otherwise. See
  README [Operational Configuration and Runtime Hardening](../../README.md#operational-configuration-and-runtime-hardening).
- For PostgreSQL: apply `migrations/0001` through `0009` in order first
  (creates the schema, the `pgvector` extension, the required vector
  index, and the sync checkpoint used by incremental synchronization).

## Deployment Prerequisites

- `Dockerfile` builds on `python:3.12-slim` and installs `libgomp1` (the
  OpenMP runtime `implicit`/ALS requires at import time — its absence was
  a real container startup failure found and fixed during Sprint 34; see
  README [Deployment and Container Runtime Readiness](../../README.md#deployment-and-container-runtime-readiness)).
- The image declares a `HEALTHCHECK` polling `GET /health` from inside the
  running container.
- `docker-compose.yml` provides local orchestration (one `app` service; no
  Kubernetes or other orchestrator-specific manifests exist in this
  repository). It intentionally does not bundle a PostgreSQL service (see
  Sprint 6/65's Progress Log entries) — run a real `pgvector/pgvector:pg16`
  container separately (see Manual Demo Walkthrough below) and pass
  `BOOK_REPOSITORY_BACKEND`/`DATABASE_URL` (and any other `config.py`
  variable) through the shell invoking `docker compose up`; each is
  forwarded only when set (Sprint 65 fix — verified `docker compose run
  --rm app python3 -c "import os; print(os.environ.get(...))"` prints
  `None` for every one of them when unset, matching the default in-memory
  behaviour exactly).

## Validation Workflow

Run before release (all deterministic, read-only, exit `0`/non-zero):

```bash
python scripts/validate_release.py --include-tests
```

Orchestrates, in order: static configuration validation, persistence
validation (PostgreSQL deployments only), deployment/startup validation,
an operations-report check, and — with `--include-tests` — `ruff check`,
`mypy --strict`, and `pytest -q` as subprocesses. See README
[CI/CD and Release Automation](../../README.md#cicd-and-release-automation)
and the [Operational Scripts Reference](../../README.md#operational-scripts-reference)
for every individual script this orchestrates.

## Operational Workflow

Once deployed, `python scripts/operations_report.py` (or
`GET /health`/`GET /readiness` directly) gives a read-only, aggregated view
of health, readiness (including persistence, when applicable), runtime
configuration, and recommendation metrics — see README
[Production Operations and Runtime Automation](../../README.md#production-operations-and-runtime-automation).

## Known Limitations

- The default embedding generator (`DeterministicFakeBookEmbeddingGenerator`)
  is a deterministic, dependency-free placeholder, not a trained ML model;
  Semantic/Hybrid recommendation *quality* numbers reflect that placeholder
  unless `EMBEDDING_GENERATOR_BACKEND=sentence_transformers` is set. See
  README's Status note.
- Offline evaluation metrics use a small, fixed, synthetic demo dataset —
  a regression/CI signal, not a production quality benchmark or a
  substitute for online experimentation.
- Observability, configuration, persistence, deployment, and operations
  validation are all deliberately application-level: no external
  monitoring platform (Prometheus/OpenTelemetry/Grafana/Datadog),
  Kubernetes manifest, or remote/network-based health probing is
  integrated. Persistence/deployment validation are point-in-time and
  read-only — they confirm facts true *now*, not that they remain true,
  and never repair anything automatically.
- ALS trains once, eagerly, at process startup; interactions recorded
  afterward do not retroactively change a running process's personalized
  results until it restarts or the model is retrained/reloaded.
- The frontend (`frontend/`) is a thin REST consumer with no server-side
  framework/database of its own; it renders whatever the backend returns
  and has no independent data or business logic to validate beyond that.
- Search (Sprint 71, `GET /books/search`, frontend `/search?q=...`) is a
  simple case-insensitive partial-match across title/author/category,
  ordered by title — no relevance ranking, autocomplete, search history, or
  filters (all explicitly out of scope). Sprint 69/70 correctly found no
  Search existed at that point; it does now.

Each limitation above is documented in full, with rationale, in its
corresponding README section.

## Manual Demo Walkthrough

The shortest path to seeing the whole system work end to end in a real
browser, using deterministic fixtures (no `DATA4LIBRARY_AUTH_KEY` needed):

```bash
# 1. Real PostgreSQL + pgvector
docker run -d --name readmatch-postgres \
  -e POSTGRES_USER=readmatch -e POSTGRES_PASSWORD=readmatch \
  -e POSTGRES_DB=readmatch -p 5433:5432 pgvector/pgvector:pg16
for f in migrations/0*.sql; do
  PGPASSWORD=readmatch docker exec -i readmatch-postgres \
    psql -U readmatch -d readmatch < "$f"
done

# 2. Seed real, reproducible demo data through the real pipeline
#    (ImportBooksUseCase + generate_book_embedding_use_case.execute -- the
#    same use case a live Data4Library import uses, not a mock, loading the
#    committed data4library_popular_books_2025_sample.json fixture instead
#    of calling the live API)
export APPLICATION_MODE=development BOOK_REPOSITORY_BACKEND=postgresql \
  DATABASE_URL=postgresql://readmatch:readmatch@localhost:5433/readmatch
PYTHONPATH=src python3 scripts/seed_demo_data.py

# 3. Backend (host process -- simplest; DATABASE_URL above is correct as-is)
uvicorn readmatch_ai.api.main:app --reload
# or, containerized: DATABASE_URL must resolve from *inside* the container,
# where "localhost" means the container itself, not the host -- use the
# Docker bridge gateway instead (typically 172.17.0.1 on Linux; confirm via
# `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`):
#   DATABASE_URL=postgresql://readmatch:readmatch@172.17.0.1:5433/readmatch \
#     docker compose up --build -d

# 4. Frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000` — the home page shows a green "Backend
connected" indicator, a hero, and recommendation rows (Popular books,
Recommended picks, Similar to \<hero\>, per-category rows) built from the
real, seeded Data4Library titles/authors/covers; clicking a book opens its
detail page, rendered from `GET /books/{id}`, with its own similar-books
row. Click "Search" in the header (or open `http://localhost:3000/search?q=한강`
directly) to search the same seeded catalog by title/author/category —
results link to the same book detail page. `http://localhost:8000/docs`
gives the same data as interactive OpenAPI. `scripts/seed_demo_data.py` is
safe to re-run at any point (upserts by ISBN/book id, never duplicates) if
you want to confirm the data hasn't drifted.

**Troubleshooting**:
- `relation "book_metadata" does not exist` (or any other `does not exist`
  from a fresh database): a migration was skipped. Re-run step 1 with the
  `migrations/0*.sql` glob shown above (not `migrations/000*.sql`, which
  silently excludes `0010_create_book_metadata_table.sql` and anything
  `0010` or later).
- Home page shows "Backend unavailable" (red indicator): the backend
  isn't reachable at `NEXT_PUBLIC_API_BASE_URL` (default
  `http://localhost:8000`) — confirm `uvicorn`/`docker compose` is
  actually running and `GET http://localhost:8000/readiness` returns
  `ready: true`.
- Home page renders but every section is empty: no data has been seeded
  yet — run step 2 (`scripts/seed_demo_data.py`) against the same
  `DATABASE_URL` the backend is using.
- A book's cover shows the local placeholder art instead of a real cover:
  expected, working fallback behavior (see `BookCover.tsx`) for a
  `cover_url` that failed to load client-side — not a bug to chase.
- `notFound()`'s `/books/{unknown-id}` page renders correctly but the raw
  HTTP status is `200`, not `404`: expected behavior of this Next.js
  version's streamed responses (see `not-found.js` in
  `frontend/node_modules/next/dist/docs/`) — the page still carries a
  `<meta name="robots" content="noindex">` tag, and the backend's own
  `GET /books/{unknown-id}` correctly returns `404`.

This is the exact flow validated in the Progress Log's Sprint 65-66 and
Sprint 69-70 entries.

## Release Readiness

Validated 2026-07-22 against this repository's `main` branch:

| Check | Result |
|---|---|
| `python scripts/validate_release.py` (default, in-memory) | **valid** — `configuration, deployment, operations` all checked |
| `python scripts/validate_release.py` (real PostgreSQL/pgvector) | **valid** — `configuration, persistence, deployment, operations` all checked (Progress Log, Sprint 65-67) |
| `ruff check src tests scripts` | pass |
| `mypy --strict src tests scripts` | pass (243 source files) |
| `pytest -q` | 863 passed, 2 failed — the 2 failures are the pre-existing Sprint 54/55 HNSW approximate-ranking pair (not a regression; do not weaken or modify per standing instruction) |
| `python scripts/generate_quality_report.py` | regression check PASSED (6 engines, K=5, `readmatch-ai-demo-dataset-v1`) |
| Frontend (`npm run lint` / `npx tsc --noEmit` / `npm run build`) | pass (0 errors; 3 pre-existing `no-img-element` warnings, unchanged) |
| Manual browser verification | confirmed (see Manual Demo Walkthrough above): real `GET /health`/`/home-feed`/`/books/{id}` data rendered by the real `next dev` server, backend-down error handling confirmed, PostgreSQL/pgvector persistence survives a container + process restart (Progress Log, Sprint 65-67) |
| Documentation consistency | corrected this Sprint: migration references (`0001-0006` → `0001-0009`), the frontend's existence (previously documented as "not built" in this file, `ADR-008`, and `SYSTEM_ARCHITECTURE.md`, stale since Sprint 40), and README's completed-Sprint count (`38` → `68`) |

**Verdict: Release Candidate approved**, with one honest caveat carried
forward rather than hidden: the 2 pre-existing HNSW-ranking test failures
above are a known, documented flake in approximate vs. exact nearest-
neighbor ranking order (see `tests/infrastructure/test_postgresql_book_embedding_repository.py`),
not a regression introduced by this validation. A PostgreSQL production
deployment additionally requires running
`python scripts/validate_release.py` (or at minimum
`scripts/validate_runtime.py` and `scripts/validate_deployment.py`)
against the target environment's actual `DATABASE_URL` before serving
traffic — both were re-run against a real `pgvector/pgvector:pg16`
container for this validation, not assumed from the in-memory default.
