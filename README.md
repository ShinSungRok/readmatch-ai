# ReadMatch AI

**A hybrid book recommendation platform built to demonstrate production-grade
system design end to end** — a public data pipeline; Popularity, Semantic,
and implicit-ALS collaborative-filtering recommendation engines fused by a
pluggable Hybrid ranking stage; a behavior-driven personalization loop
(real user actions → an aggregated preference profile → visibly different
recommendations and reasons); and a Next.js demo UI, all built with
Domain-Driven Design, Clean Architecture, and Hexagonal Architecture.

This is a personal portfolio project. Every recommendation, explanation, and
personalization signal shown in the demo is computed live from real
(synthetic-scale) data through the actual pipeline described below — nothing
is mocked or hardcoded to look good; see the [Status note](#status-note) and
[Future Improvements](#future-improvements) for an honest account of what's
a placeholder versus production-real today.

## Core Features

- **Multi-signal recommendation** — Popularity (persisted loan counts),
  Semantic similarity (pgvector cosine distance over embeddings), and
  implicit-ALS collaborative filtering, combined by a pluggable Hybrid
  `RankingStrategy` (Weighted Score Fusion or Reciprocal Rank Fusion) and
  independently re-ranked (popularity-penalty, novelty-boost, MMR
  diversity).
- **Explainable recommendations** — every personalized result carries
  deterministic, evidence-based reasons for *why* it was recommended
  (`RecommendationExplainer`) — never a fabricated reason or confidence
  score, and zero reasons is a valid, honest answer for a cold-start item.
- **Behavior-driven personalization** — real actions (search, view a book,
  like, bookmark, rate) are recorded as typed events and aggregated into a
  User Preference Profile (favorite categories/authors, recent interests,
  recent searches) that visibly changes both the recommendation ranking
  and the reasons shown for it — see
  [User Behavior & Personalization](#user-behavior--personalization).
- **Offline evaluation** — Precision@10/Recall@10/NDCG@10/Coverage against
  a deterministic dataset, run as a regression/CI gate, not just a report.
- **Production-readiness depth** — fail-fast configuration validation,
  read-only persistence/pgvector runtime checks, deployment/startup
  validation, an aggregated operations report, and a unified release
  pipeline: the same operational rigor a real production service would
  need, built out rather than left as a demo script.
- **Full-stack, real over HTTP** — a FastAPI + PostgreSQL/pgvector backend
  and a Next.js/TypeScript frontend (`frontend/`) that consumes it
  directly over REST, with no server-side framework/database of its own.

## Tech Stack

| Layer            | Technology |
|-------------------|------------|
| Backend           | Python 3.11+, FastAPI, Pydantic |
| Data / Storage    | PostgreSQL, pgvector |
| Recommendation    | Popularity ranking, sentence embeddings (pgvector cosine similarity), implicit ALS (`implicit`), pluggable Hybrid fusion (Weighted Score / Reciprocal Rank), MMR diversity re-ranking |
| Evaluation        | Precision@10, Recall@10, NDCG@10, Coverage (deterministic offline dataset) |
| Frontend          | Next.js 16, TypeScript, Tailwind CSS |
| Runtime           | Docker / Docker Compose |
| Quality gates     | `ruff`, `mypy --strict`, `pytest` (+ `testcontainers` for real-PostgreSQL integration tests), ESLint, `tsc` |

## Diagrams and Architecture Docs

See [`docs/architecture/SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md)
for the full diagrams (system structure, recommendation flow, user behavior
data flow, and User Preference Profile generation) and
[`docs/architecture/ADR.md`](docs/architecture/ADR.md) for the architecture
decision record; the [Architecture](#architecture) section below covers the
per-layer breakdown and file paths, and
[User Behavior & Personalization](#user-behavior--personalization) walks
through the personalization loop specifically.

## Demo

No static screenshots/GIFs are included in this repository (this is a
backend-first portfolio project, developed and validated in an environment
without browser automation — see
[`docs/release/RELEASE_CANDIDATE.md`](docs/release/RELEASE_CANDIDATE.md)'s
own Known Limitations) — the walkthroughs below are the actual, runnable
demo. What each screen does:

- **Home** (`/`) — a live backend-connectivity indicator, a first-visit
  category-interest onboarding card, a hero for the top pick, a "For You"
  row personalized from your own activity, and Popularity/Hybrid/Semantic/
  category recommendation rows — every row backed by a real API call, no
  client-side mock data.
- **Search** (`/search?q=...`) — case-insensitive title/author/category
  search over the same seeded catalog.
- **Book Detail** (`/books/{id}`) — full metadata, like/bookmark/read/rate
  controls, and a "Similar books" row (semantic similarity to that book).
- **My Library** (`/library`) — every book you've liked/bookmarked/read/
  rated/disliked, grouped by type.
- **My Preferences** (`/preferences`) — your own aggregated preference
  profile: favorite categories/authors, recent interests, recent searches,
  and like/dislike counts.

Run it yourself: [Quick Start](#quick-start) below, or the guided
walkthroughs in [Try personalization](#try-personalization) and
[Preference profile (Sprint 14)](#preference-profile-sprint-14) (a
complete Guest → category interest → search → view → like/save →
recommendation change → reason → My Preferences scenario), or the fuller
[Manual Demo Walkthrough](docs/release/RELEASE_CANDIDATE.md#manual-demo-walkthrough).
Screenshot/GIF capture steps for these five screens are documented in
[`docs/demo/DEMO_ASSETS_GUIDE.md`](docs/demo/DEMO_ASSETS_GUIDE.md).

### Status note

The embedding generator wired by default
(`DeterministicFakeBookEmbeddingGenerator`) is a deterministic,
dependency-free placeholder — it derives a vector from a hash of a book's
text fields, not a real ML model. Semantic/Hybrid recommendation *quality*
numbers produced today (including in the demo above) reflect that
placeholder, not a trained embedding model. The architecture (ports,
pgvector storage, similarity search, evaluation pipeline) is real and
model-agnostic; swapping in a real model is a drop-in `BookEmbeddingGenerator`
implementation. See [Future Improvements](#future-improvements) for this and
every other known gap, stated plainly rather than glossed over.

## Contents

- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Demo](#demo)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
  - [Re-ranking](#re-ranking)
  - [Explainable Recommendations](#explainable-recommendations)
  - [Recommendation Quality Reports](#recommendation-quality-reports)
  - [Run the demo](#run-the-demo)
  - [Run the API server](#run-the-api-server)
  - [Seed demo data](#seed-demo-data)
  - [Run the frontend](#run-the-frontend)
  - [Try personalization](#try-personalization)
  - [Import real book data (optional)](#import-real-book-data-optional)
- [User Behavior & Personalization](#user-behavior--personalization)
- [API Reference](#api-reference)
- [Observability](#observability)
- [Operational Configuration and Runtime Hardening](#operational-configuration-and-runtime-hardening)
- [Persistence and Vector Runtime Validation](#persistence-and-vector-runtime-validation)
- [Deployment and Container Runtime Readiness](#deployment-and-container-runtime-readiness)
- [Production Operations and Runtime Automation](#production-operations-and-runtime-automation)
- [CI/CD and Release Automation](#cicd-and-release-automation)
- [Operational Scripts Reference](#operational-scripts-reference)
- [Testing](#testing)
- [Future Improvements](#future-improvements)

## Architecture

Hexagonal Architecture (ports and adapters): Domain and Application depend on
nothing outward-facing; Infrastructure and API depend inward on Domain
ports, never the reverse.

- `src/readmatch_ai/domain/` — entities, value objects, and ports
  (interfaces: `BookRepository`, `RecommendationEngine`,
  `RecommendationReranker`, `RecommendationExplainer`, `InteractionRepository`,
  `PreferenceSignalRepository`, `PersistenceRuntimeValidator`, ...). No
  dependency on any other layer, and no raw environment-variable access
  (see `config.py` below).
- `src/readmatch_ai/application/` — use cases (one class per capability,
  e.g. `GetRecommendationsUseCase`, `HealthCheckService`,
  `ReadinessCheckService`). Depends only on Domain ports — never on
  `ApplicationContext` itself, which is what constructs these use cases.
- `src/readmatch_ai/infrastructure/` — driven adapters: PostgreSQL/pgvector
  repositories, in-memory repositories, recommendation engines
  (Popularity/Semantic/ALS/Hybrid/Reranked), and the structured-logging
  observability adapter.
- `src/readmatch_ai/api/` — driving adapter: the FastAPI REST layer. Route
  handlers perform translation only (request → Application call → response
  model); no business logic lives in `api/`.

Four top-level, composition-root-adjacent modules sit outside these four
layers by design — each legitimately needs to touch something a Domain or
Application module deliberately can't (raw environment variables, the
composition root itself, or process-level I/O like subprocesses/HTTP test
clients), so each is kept as a thin, separately-reasoned-about orchestration
layer rather than blurring that boundary:

- `src/readmatch_ai/config.py` — env-variable parsing into typed
  configuration objects (`BookRepositoryConfig`, `EmbeddingGeneratorConfig`,
  `HybridRankingConfig`, `AlsModelConfig`, `ApplicationConfiguration`) and
  their validation errors. The one place in this codebase allowed to call
  `os.environ` directly.
- `src/readmatch_ai/application_context.py` — the composition root
  (`ApplicationContext.create()`) wiring Domain ports to concrete
  Infrastructure adapters, chosen by `config.py`'s resolved configuration.
- `src/readmatch_ai/runtime_configuration.py` — static configuration
  business-rule validation (`ApplicationConfigurationValidator`), a
  redacted runtime summary (`RuntimeConfigurationSummary`), and fail-fast
  startup orchestration (`RuntimeBootstrapValidator`), called from
  `ApplicationContext.create()` before any adapter is built.
  See [Operational Configuration and Runtime Hardening](#operational-configuration-and-runtime-hardening).
- `src/readmatch_ai/deployment_validation.py` — end-to-end,
  in-process validation that the real application actually starts and
  serves (`ContainerRuntimeValidator`).
  See [Deployment and Container Runtime Readiness](#deployment-and-container-runtime-readiness).
- `src/readmatch_ai/operations.py` — read-only aggregation of
  health/readiness/configuration/metrics into one operator-facing report
  (`OperationsService`).
  See [Production Operations and Runtime Automation](#production-operations-and-runtime-automation).
- `src/readmatch_ai/release_automation.py` — orchestrates all of the
  above into one release validation pipeline (`ReleaseAutomationService`).
  See [CI/CD and Release Automation](#cicd-and-release-automation).

For the architecture decision record and system diagram, see
[`docs/architecture/ADR.md`](docs/architecture/ADR.md) and
[`docs/architecture/SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md).
Sprint-by-sprint implementation history (what was built, why, and how it
was validated, for every completed sprint) is in
[`docs/progress/PROJECT_PROGRESS.md`](docs/progress/PROJECT_PROGRESS.md). For
a release-readiness summary (implemented capabilities, prerequisites,
validation workflow, known limitations), see
[`docs/release/RELEASE_CANDIDATE.md`](docs/release/RELEASE_CANDIDATE.md).

## Repository Structure

```text
readmatch-ai/
├── src/readmatch_ai/
│   ├── domain/            # entities, value objects, ports (no outward dependencies)
│   ├── application/       # use cases (depend only on Domain ports)
│   ├── infrastructure/    # adapters: PostgreSQL/pgvector, in-memory, recommendation engines
│   ├── api/                # FastAPI routes, Pydantic schemas (translation only)
│   ├── config.py                 # env parsing
│   ├── application_context.py    # composition root
│   ├── runtime_configuration.py  # config validation, fail-fast startup
│   ├── deployment_validation.py  # end-to-end startup/serving validation
│   ├── operations.py             # aggregated operator report
│   └── release_automation.py     # release validation pipeline
├── tests/                  # mirrors src/ layout; one test module per production module
├── scripts/                 # operator CLIs — see Operational Scripts Reference
├── migrations/              # numbered, ordered PostgreSQL/pgvector SQL migrations (0001-0009)
├── frontend/                 # Next.js/TypeScript web experience — see frontend/README.md
├── docs/
│   ├── architecture/        # ADR.md, SYSTEM_ARCHITECTURE.md
│   └── progress/            # PROJECT_PROGRESS.md — sprint-by-sprint build log
├── Dockerfile / docker-compose.yml
└── pyproject.toml
```

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
# apply migrations/*.sql in order (0001-0010) against that database first
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

### Seed demo data

The in-memory default backend starts empty; a PostgreSQL backend starts
empty too until something is imported. To populate either one with a
small, real, reproducible catalog for a demo (real Data4Library titles,
authors, categories, publishers, and cover images — not synthetic
placeholders) — so the frontend's Home page has a hero and full
recommendation sections to show right away:

```bash
PYTHONPATH=src python3 scripts/seed_demo_data.py
```

This loads the committed `data/raw/data4library_popular_books_2025_sample.json`
fixture through the same `ImportBooksUseCase` pipeline
`scripts/import_books.py` uses for the real Data4Library API — persisting
each book, its popularity (loan count), and its presentation metadata
(cover URL, publisher, published date) via the configured repositories,
never a direct SQL insert — then generates an embedding for every seeded
book so the Semantic/"Similar to ..." sections have real data too. It
prints how many books were newly imported/updated/left unchanged, plus
any invalid or failed records.

Safe to run more than once: it reconciles by ISBN and every write it makes
is an upsert, so re-running against the same database leaves the same
book/popularity/metadata row counts — no duplicates accumulate.

```bash
# run twice to see this for yourself: the first run reports N new,
# the second reports 0 new / N unchanged
PYTHONPATH=src python3 scripts/seed_demo_data.py
PYTHONPATH=src python3 scripts/seed_demo_data.py
```

### Run the frontend

A Next.js/TypeScript web experience (`frontend/`) consuming this REST API
directly over HTTP — no server-side framework/database of its own. With
the backend already running (above):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. See [`frontend/README.md`](frontend/README.md)
for layout, environment configuration (`NEXT_PUBLIC_API_BASE_URL`), and
frontend-specific validation (`npm run lint`, `npx tsc --noEmit`,
`npm run build`).

### Try personalization

With the backend seeded (above) and the frontend running, the Home page's
**"For You"** row (`PersonalizedForYou`, Sprint 13) is the shortest path to
seeing an interaction change a recommendation result, end to end, in the
browser:

1. Open `http://localhost:3000`. A first-time browser gets a fresh
   anonymous id (`localStorage`, no login) and the "For You" row shows a
   **"Not enough activity yet"** note — cold-start, popularity-based picks,
   same for every new visitor.
2. Click **Like** or **Bookmark** on any book (Hero, a book card, or the
   Book Detail page — `FeedbackControls`, unchanged this Sprint).
3. The "For You" row re-fetches automatically (no page reload) via the
   existing `GET /recommendations/personalized/{user_id}/explained`
   endpoint: the cold-start note disappears, the book you just liked ranks
   higher, and its reason chip now shows the backend's real evidence
   (e.g. "Popular with many readers · You have not interacted with this
   book before.") instead of the old generic per-source label.
4. Open `/library` (My Library) — the same book now appears under
   "Liked"/"Bookmarked". Un-toggle it (same button, or from the Library
   page) and it disappears from both `/library` and the next "For You"
   refresh — reverting to the pre-interaction ranking.

No new backend endpoint or ranking logic was added for this — `/recommendations/personalized/{user_id}/explained`
and its live `ExplicitFeedbackPolicy` boost/exclusion have existed since
Sprint 29/46; this Sprint only connected the frontend to them (previously,
no page ever called that endpoint at all — see Known Limitations below).

To verify the same before/after difference without a browser (e.g. in a
headless/CI environment), call the endpoint directly:

```bash
USER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
BOOK_ID=<any seeded book id, e.g. from GET /home-feed>

# Before: cold-start score (popularity/semantic fallback only)
curl -s "http://localhost:8000/recommendations/personalized/$USER_ID/explained?limit=1" | python3 -m json.tool

curl -s -X POST http://localhost:8000/interactions -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"book_id\":\"$BOOK_ID\",\"interaction_type\":\"bookmark\"}"

# After: the bookmarked book's score is boosted (ExplicitFeedbackPolicy, +0.15)
curl -s "http://localhost:8000/recommendations/personalized/$USER_ID/explained?limit=1" | python3 -m json.tool
```

**Known limitations** (pre-existing, not introduced this Sprint — see
`docs/release/RELEASE_CANDIDATE.md`'s own Known Limitations for the full
list): explicit interactions (`POST /interactions`, which both `/library`
and this row depend on) are stored in-memory only and are lost on server
restart / not shared across multiple `uvicorn` workers; and the ALS/novelty
signal only reflects data present when the process started, not
interactions recorded afterward through the live API — only the
`ExplicitFeedbackPolicy` boost/exclusion (what the walkthrough above
demonstrates) reacts live, per request.

#### Preference profile (Sprint 14)

Continuing from the same browser session:

1. Refresh `http://localhost:3000` — a first-time browser sees a
   dismissible **"What are you interested in?"** card. Pick a couple of
   categories and click "Save preferences" (or "Skip" — either dismisses
   it for good, via a `localStorage` flag).
2. Search for something (Header → Search, or `/search?q=...`), then click
   a result. This records a `search` preference signal plus a
   `search_result_click` and `view` interaction (Book Detail records the
   view on mount) — all fire-and-forget, never blocking navigation.
3. Like or bookmark that book, or one from a recommendation row (a
   `recommendation_click` is recorded the moment you click through).
4. Open `/preferences` ("My Preferences" in the header): **Favorite
   categories**/**Favorite authors** now show the liked book's own
   category/author; **Recent interests** shows the categories you
   actually viewed/clicked (ranked above your initial onboarding pick);
   **Recent searches** shows your query.
5. Back on Home, the "For You" row's reason chip for a matching book now
   reads something like *"You've recently engaged with several
   Software Engineering books. · By Robert C. Martin, one of your
   favorite authors. · Related to your recent search for 'clean code'."*
   — real evidence from the profile in step 4, not the generic label.
6. Un-like the book: `/preferences`' favorite categories/authors count
   drops accordingly (recent interests/searches are unaffected — they
   come from separate view/search signals, not the like itself).

Verify the same profile change without a browser:

```bash
USER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
BOOK_ID=<any seeded book id>

curl "http://localhost:8000/preferences/$USER_ID" | python3 -m json.tool   # all-empty, cold start

curl -X POST http://localhost:8000/interactions -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"book_id\":\"$BOOK_ID\",\"interaction_type\":\"like\"}"

curl "http://localhost:8000/preferences/$USER_ID" | python3 -m json.tool   # favorite_categories/authors now populated
curl "http://localhost:8000/recommendations/personalized/$USER_ID/explained?limit=1" | python3 -m json.tool  # reasons include favorite_category/favorite_author
```

### Import real book data (optional)

```bash
export DATA4LIBRARY_AUTH_KEY=<your key>
python scripts/import_books.py --start-date 2024-01-01 --end-date 2024-01-31
```

## User Behavior & Personalization

The personalization loop, end to end (full diagram in
[`docs/architecture/SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md#user-behavior-data-flow)):

```text
User Action (search, view a book, like, bookmark, rate, ...)
→ Behavior Event
    - Book-scoped (view / search_result_click / recommendation_click /
      like / dislike / bookmark / read / rating) -> POST /interactions
    - Not book-scoped (category_interest / search) -> POST /preference-signals
→ Preference Aggregation (GetUserPreferenceProfileUseCase -- pure counting/
  ordering over the user's own recorded events, no ranking logic)
→ User Preference Profile (favorite categories/authors, recent interests,
  recent search terms, positive/negative book ids) -- GET /preferences/{user_id}
→ Recommendation Engine (Popularity + Semantic + ALS -> Hybrid -> Re-rank;
  entirely unchanged by personalization -- the profile never alters scoring)
→ Recommendation Reason (the Domain explainer's evidence-based reasons,
  plus Application-layer reasons -- favorite_category/favorite_author/
  recent_search_match -- added only when the profile actually matches the
  ranked item) -- GET /recommendations/personalized/{user_id}/explained
→ Frontend (Home's "For You" row, RecommendationReason's chips, and the
  My Preferences page all render this live, never a client-side mock)
```

Two properties this loop deliberately preserves: the recommendation
*ranking* itself is never touched by the profile (only the stated reasons
are annotated -- ADR-006/ADR-013), and every stage degrades gracefully for
a cold-start user (no profile signal yet) rather than erroring. See
[Try personalization](#try-personalization) and
[Preference profile (Sprint 14)](#preference-profile-sprint-14) above for
a guided, runnable walkthrough of this exact flow.

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

### `GET /books/search`

Case-insensitive partial-match search across title, author, and category
(Sprint 71), reusing the same presentation/metadata enrichment as
`/home-feed` and `/books/{id}` — not the `{"items": [{"book": ..., "score":
..., "source": ...}]}` shape above, since a search match has no
recommendation score/source of its own.

| Param   | Type   | Default | Constraints |
|---------|--------|---------|-------------|
| `q`     | string | `""`    | Trimmed before matching; blank (or missing) returns `items: []`, never an error |
| `limit` | int    | 20      | `1 <= limit <= 100` |

```bash
curl "http://localhost:8000/books/search?q=clean+code"
```

```json
{
  "items": [
    {
      "id": "a2f1e6d4-2b9a-4b1e-9a3f-6b7c8d9e0f11",
      "isbn": "9780132350884",
      "title": "Clean Code",
      "author": "Robert C. Martin",
      "category": "Software Engineering",
      "publisher": "Prentice Hall",
      "description": null,
      "cover_url": "/covers/placeholder-0.svg",
      "published_date": "2008"
    }
  ]
}
```

Results are ordered by title (no relevance scoring). The frontend's
`/search` page (`?q=...`, e.g. `/search?q=clean+code` — kept in the URL so
a search is shareable/refreshable) consumes this endpoint directly; see the
Manual Demo Walkthrough below for a worked example.

### `POST /preference-signals`

Records a behavior signal that isn't scoped to a single book (Sprint 14):
an onboarding category choice (`category_interest`) or a submitted search
query (`search`). Book-scoped events (a view, a click from search results
or a recommendation row, a like/bookmark/rating/...) go through the
existing `POST /interactions` instead.

| Field         | Type   | Constraints |
|---------------|--------|-------------|
| `user_id`     | string | Must be a valid UUID |
| `signal_type` | string | `category_interest` or `search` |
| `value`       | string | Non-empty after trimming |

```bash
curl -X POST http://localhost:8000/preference-signals -H "Content-Type: application/json" \
  -d '{"user_id": "<uuid>", "signal_type": "search", "value": "healing novel"}'
```

Returns `201` with the recorded signal, or `400` for a malformed user id,
an unknown `signal_type`, or a blank `value`.

### `GET /preferences/{user_id}`

A user's aggregated User Preference Profile (Sprint 14) — favorite
categories/authors (from the user's own like/bookmark/read/rating≥4
books), recent interests (onboarding category choices plus recently
viewed/clicked book categories), recent search terms, and positive/negative
book counts. Built entirely from the user's own recorded interactions and
preference signals; no ranking or scoring logic.

```bash
curl "http://localhost:8000/preferences/<uuid>"
```

```json
{
  "favorite_categories": ["Software Engineering"],
  "favorite_authors": ["Robert C. Martin"],
  "recent_interests": ["Software Engineering"],
  "recent_search_terms": ["healing novel"],
  "positive_book_count": 1,
  "negative_book_count": 0
}
```

An unknown-but-well-formed `user_id`, or a user with no qualifying
signals yet, returns an all-empty/zero profile — not an error, the same
cold-start convention as `GET /library/{user_id}`. This profile is also
what `GET /recommendations/personalized/{user_id}/explained` uses to add
`favorite_category`/`favorite_author`/`recent_search_match` reasons (see
above); the frontend's `/preferences` page renders it directly.

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

## Production Operations and Runtime Automation

Introduced in Sprint 35: one deterministic, read-only operational status
report — aggregating health, readiness, runtime configuration, and
recommendation metrics from a real, already-running `ApplicationContext`
into a single view, without reimplementing any of the underlying Sprint
31-34 checks it draws from.

**Runtime operations workflow**:

```bash
python scripts/operations_report.py
# also run the full deployment/startup validation (Sprint 34) -- slower:
python scripts/operations_report.py --include-deployment-check
```

```
Operations report:

  mode: development
  healthy: True
  ready: True
  configuration_valid: True
  recommendation_requests: 0
  recommendation_failures: 0
  application_version: 0.1.0

Operational.
```

When any component is unhealthy, the report additionally lists exactly
which named checks are failing (reusing each check's own already-redacted
`detail`, e.g. `book_repository: RuntimeError while checking repository
availability`), and exits `1` instead of `0`.

**What's aggregated, and how**:

| Inspection | Source | Reused from |
|---|---|---|
| Health | `context.health_check_service.check()` | Sprint 31 |
| Readiness (incl. persistence) | `context.readiness_check_service.check()` | Sprint 31, extended Sprint 33 |
| Runtime configuration | `context.runtime_configuration_summary` | Sprint 32 |
| Observability / recommendation metrics | `context.recommendation_metrics_collector.snapshot()` | Sprint 31 |
| Deployment (optional, `--include-deployment-check`) | `ContainerRuntimeValidator().validate()` | Sprint 34 |

Persistence inspection has no separate field here: `GET /readiness`'s own
`persistence_runtime` check (Sprint 33) is already part of the readiness
result this report reads, so it's covered automatically whenever it
applies. Deployment inspection is opt-in and skipped by default, since it
builds an entirely fresh `ApplicationContext` (Sprint 34's own startup
simulation) — redundant and comparatively expensive to re-run from inside
an already-running instance that is, by definition, already proof its own
startup succeeded.

**Operational summary**: `RuntimeOperationsSummary` is the flat,
at-a-glance view of one report (`operational`, `mode`, `healthy`, `ready`,
`configuration_valid`, `deployment_valid` — `None` unless checked —
`recommendation_request_count`, `recommendation_failure_count`,
`application_version`) — the same "rich result + flat safe summary" pattern
Sprints 32-34 already established (`RuntimeConfigurationSummary`,
`PersistenceRuntimeSummary`, `RuntimeEnvironmentSummary`).

**Troubleshooting**: if the command itself prints `Could not build
ApplicationContext: ...` and exits `1` before any report is generated, the
application cannot start at all — the report generator gracefully
short-circuits rather than crashing, and points to
`scripts/validate_deployment.py`/`scripts/validate_runtime.py` for the full
startup diagnostics that produced the failure. Otherwise, an `Operational:
False` result always comes with the specific failing check(s) listed, not
just a bare boolean.

**Secret redaction**: this capability introduces no new redaction rules —
it only ever surfaces already-safe values from its constituent
capabilities (health/readiness `ComponentCheck.detail`, the redacted
`RuntimeConfigurationSummary`, recommendation counts/latency, and, when
checked, `DeploymentValidationViolation` messages) — never `DATABASE_URL`,
credentials, embedding vectors, or user data.

**Limitations**: this is a read-only inspection tool, not a maintenance
tool — it performs no destructive action, and cannot repair, restart, or
reconfigure anything itself; a degraded report tells an operator *what* is
wrong (by delegating to the specific Sprint 31-34 capability that already
diagnoses that category), not how to fix it beyond what that capability
already documents. The default (fast) report does not re-verify that the
application can start from scratch — pass `--include-deployment-check` for
that, understanding it is comparatively expensive.

## CI/CD and Release Automation

Introduced in Sprint 36: one deterministic release validation pipeline that
orchestrates every existing validation capability — runtime configuration,
persistence, deployment, and an operations report (Sprints 32-35) — into a
single pre-release check, without reimplementing any of them.

**Release workflow**:

```bash
python scripts/validate_release.py
# also run this project's own quality gates (ruff/mypy/pytest) as a stage:
python scripts/validate_release.py --include-tests
```

```
Release validation summary:

  mode: development
  checked: configuration, deployment, operations
  valid: True
  application_version: 0.1.0

Release valid.
```

**Validation sequence** — five stages, run in order, each reusing an
existing capability directly rather than reimplementing it:

| Stage | Reused from | Runs when |
|---|---|---|
| `configuration` | `ApplicationConfiguration`/`ApplicationConfigurationValidator` (Sprint 32) | always, first |
| `persistence` | `validate_postgresql_persistence` (Sprint 33) | `BOOK_REPOSITORY_BACKEND=postgresql` |
| `deployment` | `ContainerRuntimeValidator` (Sprint 34) | configuration valid |
| `operations` | `OperationsService` (Sprint 35) | configuration valid |
| `tests` | `ruff check` / `mypy --strict` / `pytest -q` (as subprocesses) | `--include-tests` only |

A statically invalid `configuration` stage short-circuits every later stage
— exactly as `scripts/validate_runtime.py` already does — since none of
`persistence`/`deployment`/`operations` could meaningfully run (or safely
attempt any connection) against an already-known-invalid environment, and
each would otherwise report a confusing, redundant secondary failure for
the same root cause. `tests` is off by default (it is comparatively slow —
a full `pytest -q` run); pass `--include-tests` to run it as part of the
same pipeline invocation, using the exact same three commands
`.github/workflows/ci.yml` already runs.

**Release checklist** (what `--include-tests` covers end-to-end):

1. `ruff check src tests scripts` passes;
2. `mypy --strict src tests scripts` passes;
3. `pytest -q` passes;
4. runtime configuration is valid for the target environment
   (`APPLICATION_MODE`, `BOOK_REPOSITORY_BACKEND`, ...);
5. the persistence/pgvector runtime is reachable and correctly shaped
   (PostgreSQL deployments only);
6. the application actually starts and serves `GET /health`/`GET
   /readiness`/a real recommendation endpoint;
7. the resulting operations report is operational.

**Troubleshooting**: every violation names its own `stage`, so a failure
always points to exactly which of the five checks above to investigate —
and, for `configuration`/`persistence`/`deployment`, to that Sprint's own
documentation earlier in this README for the full diagnostic detail. A
`tests` violation (`<name>_failed`) names the failing command and its exit
code only, never captured stdout/stderr (which could be large or embed
environment detail) — re-run that command directly for the full output.

**Secret redaction**: this capability introduces no new redaction rules —
every violation is translated from an already-redacted upstream violation
(`ConfigurationViolation`, `PersistenceValidationViolation`,
`DeploymentValidationViolation`), or names a subprocess command/exit code
only — never `DATABASE_URL`, credentials, or any raw environment value.

**Limitations**: this orchestrates existing, already-documented validators
— it introduces no new deployment logic and no external CI platform
dependency (no GitHub Actions/GitLab CI SDK, no cloud release-management
integration); `.github/workflows/ci.yml` remains the actual CI entry point,
and this pipeline is a local, on-demand equivalent an operator can run
before pushing or tagging a release. It validates, but does not itself
perform, a release — no artifact is built, tagged, or published by this
capability.

## Operational Scripts Reference

Every script below is safe to run repeatedly against a local or
non-production environment (the two that write data, `import_books.py` and
`seed_demo_data.py`, both reconcile/upsert rather than duplicate on a
re-run); each is documented in full, with example output, in its own
section linked from the table.

| Script | Purpose | Documented in |
|---|---|---|
| `scripts/run_demo.py` | End-to-end walkthrough: seeds data, calls every recommendation endpoint, prints health/readiness/metrics and an evaluation report. | [Run the demo](#run-the-demo) |
| `scripts/generate_quality_report.py` | Structured Markdown/CSV engine-comparison report with CI-suitable regression checks. | [Recommendation Quality Reports](#recommendation-quality-reports) |
| `scripts/import_books.py` | Imports real book data from a public API into the configured repository. | [Import real book data](#import-real-book-data-optional) |
| `scripts/seed_demo_data.py` | Imports the committed Data4Library sample fixture (real titles/covers/metadata) into the configured repository, via the same pipeline as `import_books.py`, for a reproducible, offline-friendly demo dataset. | [Seed demo data](#seed-demo-data) |
| `scripts/validate_runtime.py` | Validates static configuration and, for PostgreSQL, the live persistence/pgvector runtime. No connection attempted if configuration is already invalid. | [Operational Configuration and Runtime Hardening](#operational-configuration-and-runtime-hardening), [Persistence and Vector Runtime Validation](#persistence-and-vector-runtime-validation) |
| `scripts/validate_deployment.py` | Confirms the real application starts and `GET /health`/`GET /readiness`/a recommendation endpoint all respond, in-process. | [Deployment and Container Runtime Readiness](#deployment-and-container-runtime-readiness) |
| `scripts/operations_report.py` | One aggregated, read-only operational status report from a real, running `ApplicationContext`. | [Production Operations and Runtime Automation](#production-operations-and-runtime-automation) |
| `scripts/validate_release.py` | Orchestrates all of the above (plus, optionally, `ruff`/`mypy`/`pytest`) into one pre-release check. | [CI/CD and Release Automation](#cicd-and-release-automation) |

All eight exit `0` on success and non-zero on failure, so any can be used
directly as a CI or pre-commit gate. None require a network connection or
production credentials unless a PostgreSQL backend is explicitly configured
(`seed_demo_data.py` never needs network access at all — its dataset is the
committed sample JSON file, not a live API call).

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

## Future Improvements

Stated plainly, per this project's own "never exaggerate what's built"
principle — every item below is a real, known gap, not a hidden one:

- **Real embedding model** — swap `DeterministicFakeBookEmbeddingGenerator`
  for a trained model (`EMBEDDING_GENERATOR_BACKEND=sentence_transformers`
  is already a drop-in `BookEmbeddingGenerator` implementation; it's just
  not the default, to keep the demo dependency-free and deterministic).
- **Durable explicit interactions** — `POST /interactions` and
  `POST /preference-signals` are backed by in-memory repositories only
  (a deliberate Phase-3 scope decision, not an oversight); they don't
  survive a server restart or share state across multiple `uvicorn`
  workers. A PostgreSQL adapter for both would close this gap without
  touching any Domain contract.
- **Live ALS retraining** — the ALS model trains once at process startup;
  ratings/likes recorded afterward boost/exclude live via
  `ExplicitFeedbackPolicy`, but don't retrain the collaborative-filtering
  model itself until the process restarts or the model is reloaded.
- **Two known inefficiencies, not correctness bugs** — `GetPersonalLibraryUseCase`
  resolves each library item's book presentation individually instead of
  batching (the `execute_many` pattern `GetHomeFeedUseCase`/
  `GetBookDetailUseCase` already use); `ALSRecommendationEngine.recommend`
  looks up one book at a time per candidate examined rather than batching
  the final candidate set.
- **Search** — currently a case-insensitive partial match, ordered by
  title only; no relevance ranking, autocomplete, search history, or
  filters.
- **Onboarding categories** — the first-visit category picker offers a
  small, hardcoded list rather than one derived from the live catalog's
  own (much more granular) category strings; it only ever feeds
  `recent_interests` (display-only), never the favorite-category
  matching used in recommendation reasons, so this is a cosmetic gap.
- **No account system** — a user is an opaque, `localStorage`-backed
  anonymous id, by design (Phase 3 explicitly excludes login/auth/session
  management); a user's history doesn't follow them across browsers/devices.
- **Real timestamps on behavior events** — "recent" interests/searches are
  approximated from each repository's own natural append order, not an
  actual recorded time; precise cross-signal recency would need a
  timestamp field added to `UserInteraction`/`UserPreferenceSignal`.
- **Collaborative filtering / ranking algorithm changes** — intentionally
  out of this project's current scope (see `docs/agent/PROJECT_INSTRUCTIONS.md`);
  the architecture (independent `RecommendationEngine`s, a pluggable
  `RankingStrategy`, a composable `RecommendationReranker`) is designed to
  accept a new algorithm as an additional adapter without touching
  existing ones, whenever that's actually planned.

See `docs/progress/PROJECT_PROGRESS.md`'s per-sprint "Deferred Items"
sections for the full, dated history behind each of these, and
`docs/release/RELEASE_CANDIDATE.md`'s Known Limitations for the
release-readiness framing of the same gaps.
