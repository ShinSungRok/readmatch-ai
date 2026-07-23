# Project Knowledge

Record only stable facts discovered during development.

## Current Facts

- Project: ReadMatch AI
- Domain: Hybrid book recommendation
- Data: Public book data plus clearly labeled synthetic interactions
- Baseline: Popularity
- Semantic: Book metadata embeddings
- Collaborative: Implicit ALS
- Hybrid: Normalized weighted scoring
- Diversity: MMR
- Evaluation: Precision@10, Recall@10, NDCG@10, Coverage
- Storage: PostgreSQL, pgvector (no separate Parquet/offline-file storage
  layer was built — see ADR-001)

## Update Rule

Add only facts that are:

- Confirmed by code or approved decisions
- Useful in future Tasks
- Not already recorded elsewhere

Do not record temporary guesses or Task reports.