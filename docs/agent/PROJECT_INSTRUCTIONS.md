# Project Instructions

## Project

ReadMatch AI is a production-oriented hybrid book recommendation portfolio.

Core capabilities:

* Public book-data pipeline
* Popularity recommendation
* Semantic recommendation
* Implicit ALS
* Hybrid ranking
* MMR diversity
* Offline evaluation
* FastAPI
* PostgreSQL and pgvector
* Next.js demonstration UI

## Roles

Planning Agent:

* Architecture
* Roadmap
* Sprint and Task definition
* Completion review

Developer Agent:

* Review
* Implementation
* Test
* Validation
* Progress log
* Commit
* Stop

## Scope

Do not independently:

* Add features
* Change architecture
* Change algorithms or weights
* Change evaluation rules
* Start the next Task
* Introduce new infrastructure
* Refactor unrelated code

## Principles

* Review before coding.
* Reuse before creating.
* Prefer the smallest complete change.
* Keep outputs deterministic and testable.
* Clearly label synthetic data.
* Do not exaggerate features or evaluation results.

## Approved Direction

* Backend: Python, FastAPI, Pydantic
* Data: PostgreSQL, pgvector, Parquet
* Recommendation: popularity, embeddings, implicit ALS, hybrid, MMR
* Evaluation: Precision@10, Recall@10, NDCG@10, Coverage
* Frontend: Next.js, TypeScript
* Runtime: Docker Compose

Out of scope unless approved:

* Kafka
* Kubernetes
* Online learning
* Deep recommender models
* Learning to Rank
* Microservices
* Enterprise MLOps