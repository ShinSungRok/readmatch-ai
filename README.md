# ReadMatch AI

A production-oriented hybrid book recommendation portfolio project, built with
Domain-Driven Design, Clean Architecture, and Hexagonal Architecture.

Core capabilities: public book-data import, popularity recommendation,
semantic (embedding) recommendation, hybrid (popularity + semantic) ranking,
offline evaluation, and a FastAPI recommendation service backed by PostgreSQL
and pgvector.

> **Status note:** the embedding generator wired by default
> (`DeterministicFakeBookEmbeddingGenerator`) is a deterministic,
> dependency-free placeholder — it derives a vector from a hash of a book's
> text fields, not a real ML model. Semantic/Hybrid recommendation *quality*
> numbers produced today (including in the demo below) reflect that
> placeholder, not a trained embedding model. The architecture (ports,
> pgvector storage, similarity search, evaluation pipeline) is real and
> model-agnostic; swapping in a real model is a drop-in `BookEmbeddingGenerator`
> implementation.

## Architecture

- `src/readmatch_ai/domain/` — entities, value objects, and ports (interfaces).
  No dependency on any other layer.
- `src/readmatch_ai/application/` — use cases. Depends only on Domain ports.
- `src/readmatch_ai/infrastructure/` — driven adapters: PostgreSQL/pgvector
  repositories, in-memory repositories, recommendation engines.
- `src/readmatch_ai/api/` — driving adapter: the FastAPI REST layer.
- `src/readmatch_ai/application_context.py` — the composition root wiring
  ports to concrete adapters (`ApplicationContext.create()`).

For the full architecture decision record and system diagram, see
[`docs/agent/architecture/ADR.md`](docs/agent/architecture/ADR.md) and
[`docs/agent/architecture/SYSTEM_ARCHITECTURE.md`](docs/agent/architecture/SYSTEM_ARCHITECTURE.md).
Sprint-by-sprint implementation history is in
[`docs/progress/PROJECT_PROGRESS.md`](docs/progress/PROJECT_PROGRESS.md).

## Quick Start

Requires Python 3.11+.

```bash
# Install with dev dependencies (lint/type-check/test tooling)
pip install -e ".[dev]"

# Lint, type-check, test
ruff check src tests scripts
mypy src tests scripts
pytest -q
```

By default the app uses in-memory repositories — no database required. To use
PostgreSQL/pgvector instead, set:

```bash
export BOOK_REPOSITORY_BACKEND=postgresql
export DATABASE_URL=postgresql://user:pass@localhost:5432/readmatch
# apply migrations/*.sql in order (0001, 0002, 0003, 0004) against that database first
```

### Run the demo

A self-contained, deterministic, end-to-end walkthrough: seeds a small book
dataset, calls the real Popularity/Semantic/Hybrid REST endpoints in-process,
and prints an offline evaluation report.

```bash
python scripts/run_demo.py
python scripts/run_demo.py --limit 5 --k 5   # show/evaluate top 5 instead of top 3
```

### Run the API server

```bash
uvicorn readmatch_ai.api.main:app --reload
# or:
docker compose up --build
```

Then visit `http://localhost:8000/docs` for interactive OpenAPI documentation,
or `http://localhost:8000/openapi.json` for the raw schema.

### Import real book data (optional)

```bash
export DATA4LIBRARY_AUTH_KEY=<your key>
python scripts/import_books.py --start-date 2024-01-01 --end-date 2024-01-31
```

## API Reference

All endpoints are `GET` and return `{"items": [...]}`, where each item has the
shape `{"book": {...}, "score": <float>, "source": <string>}`.

### `GET /recommendations/popularity`

Ranks books by persisted loan count.

| Param   | Type | Default | Constraints |
|---------|------|---------|-------------|
| `limit` | int  | 10      | `1 <= limit <= 100` |

```bash
curl "http://localhost:8000/recommendations/popularity?limit=2"
```

```json
{
  "items": [
    {
      "book": {
        "id": "a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11",
        "isbn": "9780062316097",
        "title": "Sapiens",
        "author": "Yuval Noah Harari",
        "category": "History"
      },
      "score": 200.0,
      "source": "popularity"
    },
    {
      "book": {
        "id": "b3f2e7d5-3c0b-4c2f-8b4a-7c8d9e0f1122",
        "isbn": "9780441013593",
        "title": "Dune",
        "author": "Frank Herbert",
        "category": "Science Fiction"
      },
      "score": 150.0,
      "source": "popularity"
    }
  ]
}
```

### `GET /recommendations/semantic/{book_id}`

Ranks books by embedding similarity to `book_id`, excluding that book itself.
Returns `{"items": []}` (not a 404) if `book_id` doesn't exist or has no
embedding yet. A malformed `book_id` returns `400 {"detail": "..."}`.

| Param   | Type | Default | Constraints |
|---------|------|---------|-------------|
| `limit` | int  | 10      | `1 <= limit <= 100` |

```bash
curl "http://localhost:8000/recommendations/semantic/a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11?limit=2"
```

### `GET /recommendations/hybrid`

Combines popularity and semantic signals (min-max normalized, weighted sum).
`book_id` is optional — omitting it degrades gracefully to the popularity
signal alone.

| Param     | Type          | Default | Constraints |
|-----------|---------------|---------|-------------|
| `limit`   | int           | 10      | `1 <= limit <= 100` |
| `book_id` | string (UUID) | none    | optional |

```bash
curl "http://localhost:8000/recommendations/hybrid?book_id=a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11&limit=2"
```

## Testing

```bash
pytest -q                       # full suite (unit, application, integration, API)
pytest tests/api -q             # API layer only
pytest tests/test_run_demo.py   # demo smoke test
```

Integration tests that need PostgreSQL/pgvector spin up a disposable
`pgvector/pgvector:pg16` container via `testcontainers` automatically — Docker
must be available, but no manual setup is required.
