# Release Candidate

- Project: ReadMatch AI
- Version: `0.1.0` (`pyproject.toml`)
- Status: **Release Candidate — validated 2026-07-21**
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

No frontend/UI was built; the REST API's interactive OpenAPI documentation
(`/docs`) and `scripts/run_demo.py` are the primary ways to explore system
behaviour (see [ADR-008](../architecture/ADR.md)).

## Runtime Prerequisites

- Python 3.11+ (`pyproject.toml`'s `requires-python`).
- `pip install -e ".[dev]"` for lint/type-check/test tooling.
- No database required by default — `BOOK_REPOSITORY_BACKEND` defaults to
  `in_memory`. For a real deployment, `APPLICATION_MODE=production` and a
  persistent `BOOK_REPOSITORY_BACKEND=postgresql` (with `DATABASE_URL`)
  are required together — the application refuses to start otherwise. See
  README [Operational Configuration and Runtime Hardening](../../README.md#operational-configuration-and-runtime-hardening).
- For PostgreSQL: apply `migrations/0001` through `0006` in order first
  (creates the schema, the `pgvector` extension, and the required vector
  index).

## Deployment Prerequisites

- `Dockerfile` builds on `python:3.12-slim` and installs `libgomp1` (the
  OpenMP runtime `implicit`/ALS requires at import time — its absence was
  a real container startup failure found and fixed during Sprint 34; see
  README [Deployment and Container Runtime Readiness](../../README.md#deployment-and-container-runtime-readiness)).
- The image declares a `HEALTHCHECK` polling `GET /health` from inside the
  running container.
- `docker-compose.yml` provides local orchestration; no Kubernetes or
  other orchestrator-specific manifests exist in this repository.

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
- No frontend/UI exists — the OpenAPI docs and the demo script are the
  primary way to explore the system's behaviour without writing code.

Each limitation above is documented in full, with rationale, in its
corresponding README section.

## Release Readiness

Validated 2026-07-21 against this repository's `main` branch:

| Check | Result |
|---|---|
| `python scripts/validate_release.py --include-tests` | **valid** — `configuration, deployment, operations, tests` all checked |
| `ruff check src tests scripts` | pass |
| `mypy --strict src tests scripts` | pass (178 source files) |
| `pytest -q` | pass (595 tests) |
| Deterministic repeated execution | confirmed — two consecutive `validate_release.py` runs produced byte-identical output |
| Documentation consistency | confirmed — README table-of-contents anchors verified against actual headers; no references to unimplemented features (frontend, Parquet) remain in linked documentation |

**Verdict: Release Candidate approved.** No known release blockers under
the default (in-memory, development-mode) configuration. A PostgreSQL
production deployment additionally requires running
`python scripts/validate_release.py --include-tests` (or at minimum
`scripts/validate_runtime.py` and `scripts/validate_deployment.py`)
against the target environment's actual `DATABASE_URL` before serving
traffic, since persistence/deployment validation are environment-specific
and were exercised here only against the default in-memory configuration.
