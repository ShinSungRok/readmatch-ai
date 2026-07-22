# Architecture Decisions

- ADR-001: PostgreSQL is the operational source of truth; pgvector stores
  and searches embeddings in the same database — no separate vector store
  and no Parquet/offline-file storage layer.
- ADR-002: Popularity (persisted loan count) is the baseline and cold-start
  fallback for every recommendation pathway.
- ADR-003: Semantic similarity (embeddings) and implicit-ALS collaborative
  filtering generate independent candidate sets. The embedding provider is
  swappable behind a `BookEmbeddingGenerator` port — a deterministic,
  dependency-free placeholder by default, Sentence Transformers opt-in.
- ADR-004: Hybrid ranking is a pluggable `RankingStrategy` — Weighted Score
  Fusion (default) or Reciprocal Rank Fusion — selected at composition
  time, never hardcoded into `HybridRecommendationEngine`.
- ADR-005: Re-ranking (popularity-penalty, novelty-boost, MMR diversity) is
  a separate stage applied after Hybrid ranking, not inside it, via a
  composable `RecommendationReranker` — a `RecommendationEngine`'s job
  stays candidate generation and fusion only.
- ADR-006: Recommendation explanations are derived from the already-produced
  ranked result (`RecommendationExplainer`) — never a second, independent
  ranking pass, and never a fabricated reason.
- ADR-007: Offline evaluation (Precision/Recall/MAP/NDCG/Hit-Rate/
  Diversity@K, Catalog Coverage, Novelty) is mandatory and reproducible
  against a deterministic dataset; it is a regression/sanity signal for
  development and CI, not a substitute for online experimentation.
- ADR-008: FastAPI serves recommendations over REST, with OpenAPI docs as
  an interactive reference. A Next.js/TypeScript frontend (`frontend/`,
  Sprints 40-49) is also implemented, consuming this REST API directly
  over HTTP with no server-side framework/database of its own; `/docs` and
  `scripts/run_demo.py` remain the primary ways to explore system
  behaviour without a browser.
- ADR-009: Docker (with a container-level `HEALTHCHECK`) provides the
  container runtime; `docker-compose.yml` provides local orchestration. No
  Kubernetes or other orchestrator-specific manifests exist in this
  repository.
- ADR-010: Production readiness is a first-class, incrementally-built
  capability, not an afterthought: fail-fast configuration validation,
  read-only persistence/pgvector runtime validation, deployment/container
  startup validation, an aggregated read-only operations report, and a
  unified release validation pipeline are layered on top of the
  recommendation pipeline — each reusing the layer beneath it rather than
  duplicating any check. See `docs/progress/PROJECT_PROGRESS.md`
  (Sprints 31-36) for the full build history.
- ADR-011: Observability (structured recommendation execution logging,
  in-process metrics, health/readiness endpoints) is application-level
  only. No external monitoring platform (Prometheus, OpenTelemetry,
  Grafana, Datadog) is integrated.
- ADR-012: Online learning and Learning to Rank remain out of scope.

## Historical note

An early planning draft of this document referenced a Next.js/TypeScript
demonstration frontend and Parquet-based offline storage. As of Sprint 36,
neither had been built: the project's trajectory to that point implemented
a REST API plus CLI/demo tooling, investing the equivalent effort in
production-readiness depth (Sprints 31-36) instead of a UI, and this
document was corrected at the time to say so. The frontend was since built
(Sprints 40-49, see ADR-008) once that production-readiness work was
complete — the outcome PROJECT_INSTRUCTIONS.md's approved direction always
called for, just sequenced after runtime hardening rather than before it.
Parquet-based offline storage remains unbuilt (ADR-001: PostgreSQL/pgvector
is the sole persistence layer) and is not currently planned. This document
is corrected again here per the same standing rule: documentation must
reflect the current implementation, not a superseded snapshot of it.
