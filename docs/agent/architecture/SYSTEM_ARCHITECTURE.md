# System Architecture

## Pipeline

```text
Public Book Data
→ Collection
→ Normalization
→ PostgreSQL / Parquet
→ Features / Embeddings
→ Candidate Generation
→ Score Normalization
→ Hybrid Ranking
→ MMR
→ Evaluation
→ FastAPI
→ Next.js
```

## Candidate Sources

* Popularity
* Semantic similarity
* Collaborative filtering

## Main Boundaries

* Data Pipeline
* Domain
* Recommendation
* Evaluation
* API
* Frontend
* Infrastructure

## Data Rules

PostgreSQL is the operational source of truth.

Embeddings, models, indexes, recommendations, and reports are derived artifacts and must be reproducible.

## Ranking Rules

* Normalize model scores before combining.
* Preserve candidate source and score.
* Apply approved hybrid weights.
* Apply MMR as a separate re-ranking stage.
* Use popularity as the cold-start fallback.