# ReadMatch AI

A production-oriented hybrid book recommendation portfolio project, built with
Domain-Driven Design, Clean Architecture, and Hexagonal Architecture.

Core capabilities: public book-data import, popularity recommendation,
semantic (embedding) recommendation, implicit-ALS collaborative filtering,
hybrid ranking (fuses Popularity + Semantic + ALS via a pluggable
`RankingStrategy` — Weighted Score Fusion or Reciprocal Rank Fusion), an
independent re-ranking stage (diversity, novelty, popularity-penalty
policies, composable via a `RecommendationReranker`), a personalized
recommendation REST endpoint routing a user through the full
Hybrid-ranking-then-re-ranking pipeline, deterministic structured
explanations for why a book was recommended (via a `RecommendationExplainer`),
offline evaluation, production observability (health/readiness endpoints,
structured recommendation execution logging, in-process operational metrics),
fail-fast operational configuration validation with a redacted runtime
summary, read-only production persistence/pgvector runtime validation
integrated with readiness, deterministic deployment/container runtime
validation, and a FastAPI recommendation service backed by PostgreSQL and
pgvector.

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
# apply migrations/*.sql in order (0001-0006) against that database first
```

The Hybrid engine's fusion algorithm is selected independently via:

```bash
export HYBRID_RANKING_STRATEGY=weighted   # default: min-max normalized weighted sum
export HYBRID_RANKING_STRATEGY=rrf        # Reciprocal Rank Fusion (rank-based, score-scale-agnostic)
```

### Re-ranking

A dedicated stage applied *after* Hybrid ranking, not inside it — a
`RecommendationEngine`'s job stays candidate generation/fusion only.
`RerankedRecommendationEngine` (Infrastructure) wraps any
`RecommendationEngine` and delegates to a `RecommendationReranker`
(Domain port), over-fetching extra candidates first so the reranker has a
genuine pool to select a diverse limit-sized result from rather than just
reordering an already-truncated list.

`DefaultRecommendationReranker` composes an ordered list of independent,
individually swappable `RerankingPolicy` implementations — reordering, adding,
or removing policies doesn't require touching `HybridRecommendationEngine` or
the Application layer:

- `PopularityPenaltyPolicy` — damps over-exposure of already-popular books.
- `NoveltyBoostPolicy` — boosts books a given user hasn't already interacted
  with (a no-op when the query has no `user_id`).
- `MMRDiversityPolicy` — Maximal Marginal Relevance-style diversification;
  balances each candidate's relevance against its similarity (by default, a
  same-category proxy) to items already selected.

The default composition applied to `ApplicationContext`'s
`reranked_recommendation_engine` is Popularity Penalty → Novelty Boost → MMR
Diversity, always truncated back down to the originally requested count. It's
exposed over REST as `GET /recommendations/personalized/{user_id}` — see the
API Reference below.

### Explainable Recommendations

Structured, deterministic reasons for *why* a book was recommended, exposed
via `GET /recommendations/personalized/{user_id}/explained` (see API
Reference below). Implemented independently of any concrete
`RecommendationEngine`, FastAPI, Pydantic, PostgreSQL, pgvector, ALS
internals, or Sentence Transformers internals — a `RecommendationExplainer`
(Domain port) only inspects an already-produced ranked result; it never runs
a second, independent ranking pass.

`DefaultRecommendationExplainer` supports five reason types, each gated on
actual evidence — never fabricated, and never claimed unless the available
context supports it:

| Type | Message | Evidence |
|------|---------|----------|
| `popularity` | "Popular with many readers." | The book's own `RecommendationItem.contributing_sources` includes the Popularity signal — i.e. `PopularityRecommendationEngine` actually produced it as a candidate, not merely that it was queried. |
| `semantic_similarity` | "Similar in topic to the selected book." | `contributing_sources` includes the Semantic signal (requires a `book_id`). |
| `collaborative_behavior` | "Readers with similar interests also engaged with this book." | `contributing_sources` includes the ALS signal (requires a `user_id`). |
| `novelty` | "You have not interacted with this book before." | The user (`user_id`) has no recorded interaction with this book. Absent without a `user_id`. |
| `diversity` | "Adds variety to your recommendation list." | This is the first book in the returned list whose category hasn't appeared yet (never claimed for the very first item — nothing precedes it to be diverse relative to). |

`RecommendationItem` carries a `contributing_sources` field (distinct from
`source`, which collapses to `"hybrid"` once `HybridRecommendationEngine`
fuses multiple signals) recording which underlying signals actually produced
each book as a candidate — the smallest addition needed to make
`popularity`/`semantic_similarity`/`collaborative_behavior` truthful once
fusion has happened, without rewriting the Hybrid or Re-ranking pipeline.

An item's `reasons` list may be empty, or shorter than five, whenever
evidence is limited — e.g. a popularity-only fallback for a cold-start user
with no `book_id` and no interaction history. Reasons are returned in a
fixed canonical order (`popularity`, `semantic_similarity`,
`collaborative_behavior`, `novelty`, `diversity`) regardless of computation
order, and carry no confidence/probability value.

> **Explanation, not proof:** these reasons communicate observable signals
> and system rationale — they are not mathematical proof that any single
> signal alone caused a book's exact ranking position. Multiple policies and
> signals combine into one final score; a reason confirms a signal
> contributed, not how much it weighed relative to the others.

### Recommendation Quality Reports

Compares all current recommendation engines — Popularity, Semantic, ALS,
Hybrid (Weighted), Hybrid (RRF), Hybrid + Re-ranking — against the same
deterministic evaluation dataset, and produces a structured, exportable
report:

```bash
python scripts/generate_quality_report.py
python scripts/generate_quality_report.py --k 10 --output-dir reports --baseline semantic
```

Writes `quality_report.md` and `quality_report.csv` to `--output-dir`
(default: `reports/`, not committed — see `.gitignore`), prints a concise
summary, and exits non-zero if a regression check fails (see below) — this
is the offline analytics counterpart to `scripts/run_demo.py`'s REST
walkthrough, built entirely on the same, already-existing Evaluation
Framework (`EvaluateRecommendationEngineUseCase`) rather than a second,
parallel one.

**Supported metrics** (all higher-is-better; see
`src/readmatch_ai/domain/evaluation_metrics.py` for the exact formulas):

| Metric | Meaning |
|---|---|
| `precision_at_k` | Fraction of the top-K recommendations that are relevant. |
| `recall_at_k` | Fraction of all relevant books surfaced in the top-K. |
| `map_at_k` | Mean Average Precision@K — rewards relevant books appearing earlier in the ranking. |
| `ndcg_at_k` | Normalized Discounted Cumulative Gain@K — rank-sensitive relevance. |
| `hit_rate_at_k` | Fraction of cases with at least one relevant book in the top-K. |
| `diversity_at_k` | Fraction of distinct categories within the top-K list itself (not ground-truth-based). |
| `coverage` | Fraction of the whole catalog reached by an engine's recommendations across the entire run. |
| `novelty_at_k` | Mean self-information novelty of the top-K (`-log2(popularity / catalog total)`, so rarer books score higher); `N/A` when no recommended book has recorded popularity evidence. |

**Best engine and baseline:** for each metric, the report names the
best-performing engine (ties broken deterministically — the first-listed
engine among a tie always wins, run to run) and, for every engine, a delta
from a configured **baseline engine** (`--baseline`, default: `popularity`,
matching the existing `HybridRankingConfig`/`ApplicationContext` convention
of Popularity as the cold-start/comparison baseline throughout this
project). A delta is a plain numeric difference (`engine value − baseline
value`) — the report never claims statistical significance.

**Example Markdown output** (excerpt):

```markdown
## Engine Comparison

| Engine | precision_at_k | recall_at_k | ... |
|---|---|---|---|
| popularity | 0.2250 | 0.6250 | ... |
| hybrid_reranked | 0.2500 | 0.7500 | ... |

## Best-Performing Engine by Metric

| Metric | Best Engine | Higher is Better |
|---|---|---|
| hit_rate_at_k | semantic | True |
```

**Example CSV output** (excerpt): one row per engine, one column per metric,
plus a `<metric>_delta_from_baseline` column per metric —

```csv
engine,precision_at_k,recall_at_k,...,precision_at_k_delta_from_baseline,...
popularity,0.225,0.625,...,0.0,...
hybrid_reranked,0.25,0.75,...,0.025,...
```

**Regression checks:** `scripts/generate_quality_report.py` runs a small,
committed set of default thresholds (`DEFAULT_REGRESSION_THRESHOLDS` in that
script) against `hybrid_reranked` — the full personalized pipeline — after
generating the report, calibrated against this repo's own deterministic
demo dataset (not a guess at production quality). Each threshold is either
an absolute floor (`minimum_value`) or a maximum allowed drop below the
report's baseline engine (`max_regression_from_baseline`), or both; a
violated or unverifiable (e.g. referencing an engine/metric with no value)
threshold produces a clear, per-engine-and-metric failure message, and the
script exits `1`. This is intended to run in CI exactly like `pytest` — no
network access, model downloads, or production infrastructure required.

**Deterministic dataset limitations:** the report always evaluates the same
small, hand-picked, in-memory demo dataset (`scripts/demo_fixtures.py`,
shared with `run_demo.py`) — reproducible and CI-suitable, but not a
substitute for evaluating against real usage data. Category-based "relevant
books" ground truth is a demo-only heuristic (see Status note above), and
embeddings are the deterministic placeholder generator unless
`EMBEDDING_GENERATOR_BACKEND=sentence_transformers` is set.

> **Offline metrics are not the same as real user satisfaction.** These
> numbers measure agreement with a fixed, synthetic ground truth on a fixed,
> tiny catalog — not what real users would actually click, read, or enjoy.
> Higher diversity can trade off against relevance (see `diversity_at_k` vs.
> `precision_at_k` above). A higher offline metric does not guarantee a
> better online experience. This report does not replace online experiments
> or A/B testing — it's a regression/sanity signal for development and CI,
> not a production quality benchmark.

### Run the demo

A self-contained, deterministic, end-to-end walkthrough: seeds a small book
dataset (plus synthetic user interactions for ALS), prints `GET /health` and
`GET /readiness` status, calls the real
Popularity/Semantic/Hybrid/Personalized/Explained REST endpoints in-process,
prints structured explanation reasons for one personalized request, prints
both Hybrid ranking strategies (Weighted Score Fusion vs. Reciprocal Rank
Fusion) side by side, prints the recommendation execution metrics
accumulated over the run (see Observability below), and prints an offline
evaluation report comparing Popularity, Semantic, ALS, Hybrid (Weighted),
Hybrid (RRF), and Hybrid + Re-ranking.

```bash
python scripts/run_demo.py
python scripts/run_demo.py --limit 5 --k 5   # show/evaluate top 5 instead of top 3
```

### Run the API server

```bash
# optional pre-flight: validate configuration (and, for a PostgreSQL
# backend, the live persistence/pgvector runtime) without starting anything
python scripts/validate_runtime.py

uvicorn readmatch_ai.api.main:app --reload
# or:
docker compose up --build
```

Then visit `http://localhost:8000/docs` for interactive OpenAPI documentation,
or `http://localhost:8000/openapi.json` for the raw schema. For a real
deployment, set `APPLICATION_MODE=production` and a persistent
`BOOK_REPOSITORY_BACKEND=postgresql` (see Operational Configuration and
Runtime Hardening below) — the application refuses to start with an unsafe
combination of the two.

```bash
# optional: validate that the application actually starts and serves
# correctly (GET /health, GET /readiness, a real recommendation endpoint) --
# see Deployment and Container Runtime Readiness below
python scripts/validate_deployment.py
```

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

Combines Popularity, Semantic, and ALS signals via the configured
`RankingStrategy` (`HYBRID_RANKING_STRATEGY`; see Quick Start). `book_id` and
`user_id` are both optional — omitting either degrades gracefully to whatever
sources remain active (at minimum, Popularity). Every source's contribution
is renormalized across whichever sources actually produced candidates for a
given call, so an inactive source never silently deflates the combined score.

| Param     | Type          | Default | Constraints |
|-----------|---------------|---------|-------------|
| `limit`   | int           | 10      | `1 <= limit <= 100` |
| `book_id` | string (UUID) | none    | optional |
| `user_id` | string (UUID) | none    | optional; activates the ALS signal |

```bash
curl "http://localhost:8000/recommendations/hybrid?book_id=a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11&limit=2"
```

### `GET /recommendations/personalized/{user_id}`

Routes `user_id` through `RecommendationEngine` → Hybrid ranking →
`RecommendationReranker` (popularity-penalty, novelty-boost, then
MMR-diversity, in that order — see Re-ranking above). `book_id` is optional:
providing it also blends semantic similarity to that book, exactly like the
Hybrid endpoint. `user_id` is a required path parameter (this endpoint's
whole purpose is a personalized result); a malformed one returns
`400 {"detail": "..."}`, same convention as a malformed `book_id` elsewhere.

| Param     | Type          | Default | Constraints |
|-----------|---------------|---------|-------------|
| `user_id` | string (UUID) | —       | required (path parameter) |
| `limit`   | int           | 10      | `1 <= limit <= 100` |
| `book_id` | string (UUID) | none    | optional |

```bash
curl "http://localhost:8000/recommendations/personalized/3fa85f64-5717-4562-b3fc-2c963f66afa6?limit=2"
```

```json
{
  "items": [
    {
      "book": {
        "id": "b3f2e7d5-3c0b-4c2f-8b4a-7c8d9e0f1122",
        "isbn": "9780441013593",
        "title": "Dune",
        "author": "Frank Herbert",
        "category": "Science Fiction"
      },
      "score": 0.772,
      "source": "hybrid"
    }
  ]
}
```

**Cold-start behaviour:** an unknown-but-well-formed `user_id`, a user with
no recorded interactions, or a deployment with no trained ALS model data at
all, all degrade gracefully — never a 404/500. Concretely: `NoveltyBoostPolicy`
and ALS candidate generation both treat "no interaction history for this
user" as "nothing to boost/personalize from", so the result falls back to
whatever Popularity/Semantic/`PopularityPenaltyPolicy`/`MMRDiversityPolicy`
alone would produce — the same fallback path already used when `book_id`
is omitted from the Hybrid endpoint. This is existing engine/reranker
behaviour, unchanged for this endpoint; the API layer adds no additional
existence check for `user_id`.

**Current personalization limitations:**

- ALS trains once, eagerly, when the process starts (`ApplicationContext.create()`);
  interactions recorded afterwards do not retroactively change a running
  process's personalized results until it's restarted (or `ALS_MODEL_PATH`
  is retrained/reloaded — see `AlsModelConfig`). `NoveltyBoostPolicy` and
  `PopularityPenaltyPolicy`, by contrast, read their repositories live on
  every request.
- The ranking strategy (`HYBRID_RANKING_STRATEGY`) and the re-ranking policy
  composition are both process-wide configuration, not per-request — there
  is no query parameter to pick a different strategy/policy set per call.
- Embeddings are `DeterministicFakeBookEmbeddingGenerator` by default (see
  the Status note above), so the Semantic contribution to a personalized
  result is not representative of a real model's quality.

### `GET /recommendations/personalized/{user_id}/explained`

Same pipeline and parameters as `GET /recommendations/personalized/{user_id}`
above, but each item is additionally annotated with a `reasons` array of zero
or more structured, evidence-based explanations (see Explainable
Recommendations above). The plain personalized endpoint's response shape is
completely unaffected — this is a separate, additive route, not a query
parameter on the existing one, so existing clients/responses never change.

| Param     | Type          | Default | Constraints |
|-----------|---------------|---------|-------------|
| `user_id` | string (UUID) | —       | required (path parameter) |
| `limit`   | int           | 10      | `1 <= limit <= 100` |
| `book_id` | string (UUID) | none    | optional |

```bash
curl "http://localhost:8000/recommendations/personalized/3fa85f64-5717-4562-b3fc-2c963f66afa6/explained?book_id=a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11&limit=2"
```

```json
{
  "items": [
    {
      "book": {
        "id": "b3f2e7d5-3c0b-4c2f-8b4a-7c8d9e0f1122",
        "isbn": "9780441013593",
        "title": "Dune",
        "author": "Frank Herbert",
        "category": "Science Fiction"
      },
      "score": 0.772,
      "source": "hybrid",
      "reasons": [
        {"type": "popularity", "message": "Popular with many readers."},
        {"type": "semantic_similarity", "message": "Similar in topic to the selected book."},
        {"type": "novelty", "message": "You have not interacted with this book before."}
      ]
    }
  ]
}
```

**Cold-start behaviour:** identical to the plain personalized endpoint — an
unknown/new user or a request with no `book_id` never errors. The difference
is only in which reasons can appear: without a `user_id`'s interaction
history, `novelty` never fires; without a `book_id`, `semantic_similarity`
never fires; without recorded popularity data or ALS candidacy for a given
book, `popularity`/`collaborative_behavior` don't either. A cold-start item
can legitimately have an empty `reasons` list.

### `GET /health`

Is this process itself operating normally? A lightweight, dependency-free
self-check — distinct from `GET /readiness` below, which probes external
dependencies. Returns HTTP 200 when healthy, HTTP 503 when unhealthy.

```bash
curl "http://localhost:8000/health"
```

```json
{"healthy": true, "checks": [{"name": "process", "available": true, "detail": null}]}
```

### `GET /readiness`

Are this instance's required runtime dependencies currently available to
serve requests — runtime configuration, the book repository, recommendation
engine composition, and (when the repository is genuinely PostgreSQL-backed)
the live persistence/pgvector runtime? Returns HTTP 200 when ready, HTTP 503
when not ready (e.g. the database connection has dropped).

```bash
curl "http://localhost:8000/readiness"
```

```json
{
  "ready": true,
  "checks": [
    {"name": "configuration", "available": true, "detail": null},
    {"name": "book_repository", "available": true, "detail": null},
    {"name": "recommendation_composition", "available": true, "detail": null}
  ],
  "mode": "development"
}
```

`mode` (Sprint 32) is the active `APPLICATION_MODE` — see Operational
Configuration and Runtime Hardening below.

A failing check's `detail` is always a safe, non-sensitive summary (e.g.
`"RuntimeError while checking repository availability"`) — never a raw
exception message, which could embed a database connection string.

## Observability

Introduced in Sprint 31: **application-level** observability only —
answering "is the application healthy", "is it ready to receive requests",
"which engine served a request", "how long did it take", "did fallback
behaviour occur", and "what operational failures occurred". All of it is
independent of FastAPI, Pydantic, PostgreSQL/pgvector, and any concrete
logging or monitoring library — the Domain/Application layers define plain,
transport-independent shapes (`HealthStatus`, `ReadinessStatus`,
`RecommendationExecutionRecord`, `RecommendationExecutionMetrics`); only the
Infrastructure/API layers know about `logging` or HTTP status codes.

**Health vs. Readiness** are deliberately distinct, mirroring the standard
Kubernetes liveness/readiness probe split: Health asks "is this process
alive and internally intact" (answering an HTTP request at all already
proves this); Readiness asks "can this instance currently reach what it
needs" by actually probing configuration, the book repository, and
recommendation engine composition. A process can be healthy while not
ready (e.g. its database connection just dropped).

**Structured recommendation execution logging.** Every request served
through `GET /recommendations/*` is wrapped by an `ObservedRecommendationEngine`
(Infrastructure), which times the call and emits one
`RecommendationExecutionRecord` — request id, engine name, recommendation
type, duration, recommendation count, whether a fallback (no `book_id` and
no `user_id`) was used, success/failure, and a coarse error classification
(`validation_failure` for a `ValueError`, `unexpected_failure` otherwise).
`LoggingRecommendationExecutionObserver` logs each record as one structured
message via the Python standard library's `logging` module (INFO on
success, WARNING on failure) under the `readmatch_ai.recommendation_execution`
logger — no external logging framework. **This record never includes**
user secrets, API keys, embedding vectors, ALS latent factors, raw
interaction history, or database connection information — only
identifiers, counts, and timing, by construction.

**Recommendation metrics.** `RecommendationMetricsCollector` (Application)
is the other observer fed by the same execution records, aggregating
request/success/failure/fallback counts, total and average latency, and a
per-engine usage count — a deterministic, in-process snapshot
(`RecommendationExecutionMetrics`), suitable for assertions in tests and for
the one operator-facing summary printed by `scripts/run_demo.py`. It has no
external metrics-platform integration.

**Limitations.** This Sprint introduces application-level observability
only. Distributed tracing, a Prometheus/OpenTelemetry exporter, and
integration with an external monitoring platform (Grafana, Datadog, etc.)
are explicitly out of scope here and remain future enhancements — metrics
are in-process only (reset on restart, not shared across instances), and
structured logs go to the standard `logging` module rather than a
centralized log aggregator.

## Operational Configuration and Runtime Hardening

Introduced in Sprint 32: validates runtime configuration *before* the
application begins serving, fails fast with safe, aggregated diagnostics
when configuration is invalid, and exposes a redacted structured summary of
the active runtime — independent of FastAPI, CLI argument parsing, concrete
PostgreSQL drivers, and any secret-management vendor SDK.

**Runtime modes** (`APPLICATION_MODE`, default `development`):

| Mode | Meaning |
|------|---------|
| `development` | Local/default use; permissive (in-memory/deterministic adapters allowed). |
| `test` | Automated test runs; equally permissive — no rule distinguishes it from `development` today. |
| `production` | Real deployments; the one mode with an extra safety rule (see below). |

**Configuration categories validated** — one deterministic
`ApplicationConfiguration`, aggregated from the existing per-capability
config classes already documented above (`BookRepositoryConfig`,
`EmbeddingGeneratorConfig`, `HybridRankingConfig`, `AlsModelConfig`) plus the
new runtime mode:

- runtime mode (`APPLICATION_MODE`);
- repository/persistence adapter selection (`BOOK_REPOSITORY_BACKEND`,
  `DATABASE_URL`);
- embedding adapter/model selection (`EMBEDDING_GENERATOR_BACKEND`,
  `EMBEDDING_MODEL_NAME`);
- hybrid ranking strategy selection (`HYBRID_RANKING_STRATEGY`);
- ALS model path (`ALS_MODEL_PATH`) — has no invalid values to reject.

**Validation rules**: every unknown backend/strategy/mode value; a missing
`DATABASE_URL` when `BOOK_REPOSITORY_BACKEND=postgresql`; a `DATABASE_URL`
that doesn't start with `postgresql://`/`postgres://`; and the one
cross-field production rule — `APPLICATION_MODE=production` must not use the
non-persistent `in_memory` repository backend. Every independent violation
is aggregated into one report (an operator fixing multiple problems doesn't
need multiple failed startup attempts to discover them all):

```
Configuration invalid -- 2 violation(s):

  [unknown_runtime_mode] APPLICATION_MODE: Unknown APPLICATION_MODE: 'staging' (expected one of ['development', 'production', 'test'])
  [unknown_book_repository_backend] BOOK_REPOSITORY_BACKEND: Unknown BOOK_REPOSITORY_BACKEND: 'not-a-backend' (expected one of ['in_memory', 'postgresql'])
```

**Startup behaviour**: `ApplicationContext.create()` runs this validation
*before* building any repository/engine — no PostgreSQL connection, ALS
training, or other Infrastructure I/O is ever attempted when static
configuration is already invalid. An invalid configuration raises
`RuntimeBootstrapFailure` (carrying every aggregated violation); a
`composition_failure`/`startup_succeeded` diagnostic is logged via the same
stdlib-`logging` boundary Sprint 31 established for structured recommendation
logging (`readmatch_ai.startup` logger). This never affects Fake/In-memory
adapter injection in tests — validation is env-driven and every existing
test's defaults (unset `APPLICATION_MODE`, `in_memory`/`deterministic`
backends) already pass it trivially.

**Operator validation command** — check configuration before starting the
API, without building the application or attempting any Infrastructure
connection:

```bash
python scripts/validate_runtime.py
```

```
Runtime configuration summary:

  mode: development
  book_repository_backend: in_memory
  embedding_generator_backend: deterministic
  embedding_model_name: None
  hybrid_ranking_strategy: weighted
  observability_enabled: True
  application_version: 0.1.0

Configuration valid.
```

Exits `0` for valid configuration, `1` (with every violation listed) for
invalid configuration. Uses the exact same `ApplicationConfiguration`/
`ApplicationConfigurationValidator` the real application startup path uses —
no duplicated validation rules.

**Secret redaction**: the runtime configuration summary (also reachable via
this CLI and, as an adapter-category field, `GET /readiness`'s `mode`) never
includes `DATABASE_URL`, passwords, tokens, or any raw environment value —
only the resolved *category* each capability selected (e.g.
`"postgresql"`/`"in_memory"`, never the connection string itself). Violation
messages follow the same rule; they're safe to log or print directly.

**Readiness interaction**: `GET /readiness`'s existing `configuration`
check (Sprint 31) is extended, not duplicated, to also apply these same
production-safety/form rules — so if configuration drifts to something
unsafe after startup (e.g. an operator edits an env file without
restarting), the next readiness probe reflects it. Existing healthy and
repository-failure readiness behaviour is unchanged.

**Limitations**: validation is static — it confirms structural and
operational prerequisites (well-formed values, safe mode/backend
combinations) but cannot guarantee every external dependency (the database,
a model host) remains reachable *after* startup; that's what `GET
/readiness`'s live probes are for. `test` mode currently has no rules
distinguishing it from `development` — it exists as a named, forward-looking
mode identifier, not (yet) a source of additional validation.

## Persistence and Vector Runtime Validation

Introduced in Sprint 33: read-only validation of the *live* PostgreSQL +
pgvector runtime, distinct from Sprint 32's static environment-variable
validation — confirming the actual database the application is about to
serve from has the schema, extension, and index this codebase requires,
before requests are routed to it.

**PostgreSQL runtime prerequisites** — only checked when
`BOOK_REPOSITORY_BACKEND=postgresql`; never applicable (and never attempted)
for the default `in_memory` backend:

- PostgreSQL connectivity (a plain `SELECT 1`);
- the four required tables: `books`, `book_popularity`, `book_embeddings`,
  `user_book_interactions`;
- the `pgvector` extension is installed (`CREATE EXTENSION vector`, see
  `migrations/0004_...sql`);
- `book_embeddings.vector`'s declared width matches the dimension every
  currently-wired `BookEmbeddingGenerator` actually produces (384 —
  `DeterministicFakeBookEmbeddingGenerator`'s default and
  `sentence-transformers/all-MiniLM-L6-v2`'s output size; see
  `migrations/0005_...sql`);
- the `idx_book_embeddings_vector_cosine` HNSW index required for vector
  similarity search to perform acceptably.

Every check is a read-only `SELECT` against `pg_catalog`/
`information_schema` — this capability never creates, alters, or migrates
anything; schema setup remains the job of `migrations/*.sql`, applied
separately.

**Readiness interaction**: `ApplicationContext` wires a
`PostgreSQLPersistenceRuntimeValidator` (reusing the same already-open
connection as the real repository — no second connection is opened) into
`GET /readiness` only when the composed repository is genuinely
PostgreSQL-backed; an explicit Fake/In-memory override (even with
`BOOK_REPOSITORY_BACKEND=postgresql` set in the environment) correctly
leaves persistence validation inapplicable, preserving deterministic
Fake/In-memory test composition. When applicable, an unhealthy persistence
runtime (an unreachable database, a missing table/extension/index, an
incompatible vector width) surfaces as an additional `persistence_runtime`
check and makes `GET /readiness` report Not Ready — existing `configuration`/
`book_repository`/`recommendation_composition` checks and Health semantics
are unchanged.

```json
{
  "ready": false,
  "checks": [
    {"name": "configuration", "available": true, "detail": null},
    {"name": "book_repository", "available": true, "detail": null},
    {"name": "recommendation_composition", "available": true, "detail": null},
    {
      "name": "persistence_runtime",
      "available": false,
      "detail": "pgvector_extension: The pgvector 'vector' extension is not installed"
    }
  ],
  "mode": "production"
}
```

**Operator validation command** — `scripts/validate_runtime.py` (Sprint 32)
now also validates the persistence runtime, reusing the exact same
`PostgreSQLPersistenceRuntimeValidator`/`validate_postgresql_persistence`
`GET /readiness` uses (no duplicated rules), whenever static configuration
is valid and the backend is `postgresql`:

```bash
python scripts/validate_runtime.py
```

```
Runtime configuration summary:

  mode: production
  book_repository_backend: postgresql
  ...

Configuration valid.

Persistence runtime summary:

  checked: connectivity, required_tables, pgvector_extension, vector_dimension, vector_index
  valid: True

Note: this confirms structural/operational prerequisites only -- ...
```

Exits `0` only when both static configuration *and* (when applicable)
persistence runtime validation pass; `1` otherwise, with every violation
listed (`[code] component: message`). A statically invalid configuration
short-circuits before any PostgreSQL connection is attempted — "avoid
opening production connections when static configuration is already
invalid" holds exactly as it did in Sprint 32.

**Secret redaction**: violation messages and the persistence runtime
summary never include `DATABASE_URL`, credentials, embedding vectors, or
user data — only component names, safe schema facts (e.g. `"vector(8),
expected vector(384)"`), and exception *type names* (never
`str(exception)`, which could embed connection details) for connectivity
failures.

**Limitations**: validation is read-only and point-in-time — it confirms
the schema/extension/index/connectivity facts true *right now*, not that
they will remain true, nor that data already stored is well-formed, nor
that query performance is acceptable at production scale. It checks the one
HNSW vector index this codebase's migrations create
(`idx_book_embeddings_vector_cosine`); other, non-vector indexes are out of
scope. No automatic schema creation, migration, or repair is ever
performed — a failing check means an operator must run `migrations/*.sql`
(or the relevant fix) themselves.

## Deployment and Container Runtime Readiness

Introduced in Sprint 34: end-to-end validation that the application starts
successfully and serves correctly — deterministic, requiring no real running
container, network access, or production credentials, and reusing every
prior Sprint's boundary rather than duplicating any of it: Sprint 32's
`RuntimeBootstrapValidator` (startup/configuration validation) and Sprint
31/33's real `GET /health`/`GET /readiness` endpoints (already reflecting
persistence integration when applicable).

**Deployment prerequisites**: same as documented throughout this README —
`APPLICATION_MODE`, `BOOK_REPOSITORY_BACKEND`/`DATABASE_URL` for a real
deployment, and (per the `Dockerfile`) the `libgomp1` system package, which
`implicit` (the ALS collaborative-filtering library) requires at import
time. This was a real, previously-undetected container startup failure —
`readmatch_ai.infrastructure.als_model`'s `import implicit.als` raised
`ImportError: libgomp.so.1: cannot open shared object file` inside the
`python:3.12-slim` base image, which does not include it — found and fixed
while building this Sprint's own capability, and is exactly the class of
problem "deterministic container startup validation" exists to catch.

**Container startup workflow**: the `Dockerfile` now also declares a
`HEALTHCHECK` (a plain `python -c ...` one-liner using only the standard
library — no `curl`, avoiding a new system dependency in the image) that
polls the real `GET /health` endpoint from inside the running container,
so `docker ps`/orchestrators can observe container health directly:

```bash
docker build -t readmatch-ai .
docker run -d -p 8000:8000 readmatch-ai
docker inspect --format='{{json .State.Health}}' <container>
```

**Runtime validation sequence** — `ContainerRuntimeValidator`
(`readmatch_ai.deployment_validation`) drives the exact same FastAPI app
object (`api.main.create_app()`) the `Dockerfile`'s own `uvicorn
readmatch_ai.api.main:app` entrypoint serves, via an in-process
`TestClient`:

1. **startup** — builds the real `ApplicationContext` (Sprint 32's
   `RuntimeBootstrapValidator` runs first, exactly as it does in
   production; a statically invalid configuration is reported here and
   nothing further is checked);
2. **health** — `GET /health` must return HTTP 200 with `healthy: true`;
3. **readiness** — `GET /readiness` must return HTTP 200 with `ready: true`
   (already reflecting persistence integration via the `persistence_runtime`
   check, Sprint 33, when applicable — not re-validated separately here);
4. **api** — `GET /recommendations/popularity` must return HTTP 200, a
   minimal, real proof of API availability beyond the observability
   endpoints themselves.

Every exercised endpoint is already read-only; this capability never writes
to a database, creates data, or performs any destructive initialization.

**Deployment validation command**:

```bash
python scripts/validate_deployment.py
```

```
Deployment validation summary:

  mode: development
  checked: startup, health, readiness, api
  valid: True

Deployment valid -- the application starts successfully and GET /health, GET /readiness, and a real recommendation endpoint are all reachable.
```

Exits `0` for a valid deployment, `1` otherwise, with every violation
listed (`[code] component: message`) — e.g.
`[readiness_endpoint_unhealthy] readiness: GET /readiness returned HTTP 503 (failing: book_repository)`.
Contains no validation logic of its own; reuses `RuntimeBootstrapValidator`
and the real health/readiness endpoints exclusively.

**Startup troubleshooting**: a `startup_configuration_invalid` violation
means static configuration is invalid (see Operational Configuration and
Runtime Hardening above — run `scripts/validate_runtime.py` for the full
violation list); a `startup_failed` violation means something else failed
while actually composing the application (a real dependency failure, e.g.
an unreachable PostgreSQL — see Persistence and Vector Runtime Validation
above); a `health_endpoint_unhealthy`/`readiness_endpoint_unhealthy`/
`api_endpoint_unavailable` violation means the application started but a
specific endpoint is reporting a problem — the message lists which
underlying check(s) are failing.

**Secret redaction**: violation messages never include `DATABASE_URL`,
credentials, or any raw environment value — only endpoint names, HTTP
status codes, and the names of underlying failing checks (already-redacted
per Sprint 31/32/33's own discipline).

**Limitations**: validation runs in-process (via `TestClient`, the same
mechanism this project's entire test suite already uses to validate the
API layer) against the real application code, not against a literal
running Docker container over the network — it faithfully exercises the
same production entrypoint and dependency-injection wiring, but does not
by itself prove the `Dockerfile`/image build succeeds or that the
container's own network/port configuration is correct; `docker build` +
`docker run` (as shown above) remains the way to verify those. It also does
not validate Kubernetes or other orchestrator-specific deployment manifests
— none exist in this repository today.

## Testing

```bash
pytest -q                                 # full suite (unit, application, integration, API)
pytest tests/api -q                       # API layer only
pytest tests/test_run_demo.py             # demo smoke test
pytest tests/test_generate_quality_report.py   # quality-report CLI (success, regression pass/fail, determinism)
```

Integration tests that need PostgreSQL/pgvector spin up a disposable
`pgvector/pgvector:pg16` container via `testcontainers` automatically — Docker
must be available, but no manual setup is required.
