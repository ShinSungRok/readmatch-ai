# Architecture Decisions

- ADR-001: PostgreSQL is the operational source of truth.
- ADR-002: Parquet is used for reproducible offline datasets.
- ADR-003: pgvector provides vector search.
- ADR-004: Popularity is the baseline and cold-start fallback.
- ADR-005: Semantic and ALS models generate separate candidates.
- ADR-006: Weighted normalized scores form the MVP hybrid ranker.
- ADR-007: MMR provides diversity re-ranking.
- ADR-008: Offline evaluation is mandatory.
- ADR-009: FastAPI serves recommendations.
- ADR-010: Next.js demonstrates system results.
- ADR-011: Docker Compose provides the local runtime.
- ADR-012: Online learning and Learning to Rank are outside MVP.

Only the Planning Agent may change these decisions.