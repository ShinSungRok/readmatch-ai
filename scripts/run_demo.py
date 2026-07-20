#!/usr/bin/env python3
"""End-to-end recommendation demo: seeds a deterministic dataset, exercises the
Popularity, Semantic, and Hybrid recommendation REST endpoints, and reports
offline evaluation metrics comparing Popularity, Semantic, ALS, and both
Hybrid ranking strategies (Weighted Score Fusion and Reciprocal Rank Fusion).

Runs entirely in-process against the real FastAPI app (readmatch_ai.api.main)
via FastAPI's TestClient — real HTTP routing, Pydantic validation, and JSON
responses, without needing a bound network port. No external service (real
book-data API, real database) is required; the default ApplicationContext
backend (in-memory, or PostgreSQL if BOOK_REPOSITORY_BACKEND/DATABASE_URL are
set) is used exactly as scripts/import_books.py already does.

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --limit 5 --k 5
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.ranking_strategies import (
    ReciprocalRankFusionStrategy,
    WeightedScoreFusionStrategy,
)
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.als_model import train_als_model
from readmatch_ai.infrastructure.als_recommendation_engine import ALSRecommendationEngine
from readmatch_ai.infrastructure.hybrid_recommendation_engine import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    HybridRecommendationEngine,
)


@dataclass(frozen=True)
class _SeedBook:
    isbn_12_digits: str
    title: str
    author: str
    category: str
    loan_count: int


def _isbn13(twelve_digits: str) -> str:
    """Append a valid ISBN-13 check digit to a 12-digit prefix."""
    total = sum((1 if i % 2 == 0 else 3) * int(digit) for i, digit in enumerate(twelve_digits))
    check_digit = (10 - total % 10) % 10
    return twelve_digits + str(check_digit)


# Deterministic, hand-picked across three categories so Popularity (varied
# loan_count) and category-grouping (used below as evaluation ground truth)
# produce visibly different rankings.
_SEED_BOOKS: tuple[_SeedBook, ...] = (
    _SeedBook("978000000001", "Clean Code", "Robert C. Martin", "Software Engineering", 120),
    _SeedBook(
        "978000000002", "The Pragmatic Programmer", "Andrew Hunt", "Software Engineering", 95
    ),
    _SeedBook("978000000003", "Effective Java", "Joshua Bloch", "Software Engineering", 80),
    _SeedBook("978000000004", "Dune", "Frank Herbert", "Science Fiction", 150),
    _SeedBook("978000000005", "Foundation", "Isaac Asimov", "Science Fiction", 60),
    _SeedBook("978000000006", "Neuromancer", "William Gibson", "Science Fiction", 40),
    _SeedBook("978000000007", "Sapiens", "Yuval Noah Harari", "History", 200),
    _SeedBook("978000000008", "Guns, Germs, and Steel", "Jared Diamond", "History", 30),
)


@dataclass(frozen=True)
class _SeedInteraction:
    user_label: str
    isbn_12_digits: str
    interaction_count: int


# Two overlapping readers per category cluster, so ALS has co-occurrence
# signal to learn from: "alice"/"bob" both read Software Engineering books
# (sharing "The Pragmatic Programmer"), "carol"/"dave" both read Science
# Fiction (sharing "Foundation"). "alice" is the demo's spotlight user below;
# she hasn't read "Effective Java", which "bob" has -- a book ALS should be
# able to surface for her via that shared-reader correlation.
_SEED_INTERACTIONS: tuple[_SeedInteraction, ...] = (
    _SeedInteraction("alice", "978000000001", 3),  # Clean Code
    _SeedInteraction("alice", "978000000002", 2),  # The Pragmatic Programmer
    _SeedInteraction("bob", "978000000002", 3),  # The Pragmatic Programmer
    _SeedInteraction("bob", "978000000003", 2),  # Effective Java
    _SeedInteraction("carol", "978000000004", 3),  # Dune
    _SeedInteraction("carol", "978000000005", 2),  # Foundation
    _SeedInteraction("dave", "978000000005", 3),  # Foundation
    _SeedInteraction("dave", "978000000006", 2),  # Neuromancer
)

DEMO_USER_LABEL = "alice"


def _user_id(label: str) -> UserId:
    """Deterministic UserId derived from a demo user label, for reproducible output."""
    return UserId(uuid.uuid5(uuid.NAMESPACE_DNS, f"readmatch-ai-demo-user-{label}"))


def seed_demo_dataset(context: ApplicationContext) -> list[Book]:
    """Register the demo books/interactions, record popularity, and generate embeddings."""
    books: list[Book] = []
    books_by_isbn_prefix: dict[str, Book] = {}
    for seed in _SEED_BOOKS:
        book = context.register_book_use_case.execute(
            RegisterBookInput(
                isbn=_isbn13(seed.isbn_12_digits),
                title=seed.title,
                author=seed.author,
                category=seed.category,
            )
        )
        context.book_popularity_repository.record(
            BookPopularity(
                book.id,
                loan_count=seed.loan_count,
                period_start="2024-01-01",
                period_end="2024-12-31",
            )
        )
        context.generate_book_embedding_use_case.execute(str(book.id.value))
        books.append(book)
        books_by_isbn_prefix[seed.isbn_12_digits] = book

    for interaction in _SEED_INTERACTIONS:
        context.user_book_interaction_repository.record(
            UserBookInteraction(
                user_id=_user_id(interaction.user_label),
                book_id=books_by_isbn_prefix[interaction.isbn_12_digits].id,
                interaction_count=interaction.interaction_count,
            )
        )
    return books


def _build_als_engine(context: ApplicationContext) -> RecommendationEngine:
    """Train ALS fresh from the just-seeded interactions.

    context.als_recommendation_engine was already built (on zero
    interactions) at ApplicationContext.create() time -- ALS trains once,
    eagerly, and does not retroactively reflect interactions recorded
    afterwards (see application_context.py). The demo seeds interactions
    after context creation, so it retrains here using the same
    infrastructure building blocks ApplicationContext itself uses.
    """
    model = train_als_model(context.user_book_interaction_repository.list_all())
    return ALSRecommendationEngine(
        model, context.book_repository, context.user_book_interaction_repository
    )


_EQUAL_HYBRID_WEIGHTS = {POPULARITY_SOURCE: 1 / 3, SEMANTIC_SOURCE: 1 / 3, ALS_SOURCE: 1 / 3}


def _build_hybrid_engines(
    context: ApplicationContext, als_engine: RecommendationEngine
) -> tuple[RecommendationEngine, RecommendationEngine]:
    """Build both hybrid ranking strategies from the same popularity/semantic/ALS engines."""
    weighted = HybridRecommendationEngine(
        context.recommendation_engine,
        context.semantic_recommendation_engine,
        als_engine,
        WeightedScoreFusionStrategy(dict(_EQUAL_HYBRID_WEIGHTS)),
    )
    rrf = HybridRecommendationEngine(
        context.recommendation_engine,
        context.semantic_recommendation_engine,
        als_engine,
        ReciprocalRankFusionStrategy(),
    )
    return weighted, rrf


def _build_evaluation_dataset(books: list[Book], user_id: UserId) -> EvaluationDataset:
    """Ground truth for this demo only: books in the same category are 'relevant'.

    This is a policy choice local to the demo script, not part of the
    Evaluation domain itself (EvaluationCase.relevant_book_ids is deliberately
    source-agnostic) -- a real ground-truth source is a future concern.

    Every case carries the same demo user_id alongside its book_id, so one
    dataset exercises Popularity, Semantic, ALS, and Hybrid uniformly --
    Hybrid needs both fields present to query all three sub-engines. Reusing
    one fixed user across every case is a demo-only simplification, not a
    real per-case personalization design.
    """
    cases = [
        EvaluationCase(
            book_id=book.id,
            user_id=user_id,
            relevant_book_ids=frozenset(
                other.id
                for other in books
                if other.category == book.category and other.id != book.id
            ),
        )
        for book in books
    ]
    return EvaluationDataset(cases=tuple(case for case in cases if case.relevant_book_ids))


def _print_recommendation_comparison(client: TestClient, spotlight: Book, limit: int) -> None:
    print(
        f'Recommendations similar to: "{spotlight.title.value}" by '
        f"{spotlight.author.value} ({spotlight.category.value})\n"
    )
    responses = {
        "Popularity": client.get("/recommendations/popularity", params={"limit": limit}),
        "Semantic": client.get(
            f"/recommendations/semantic/{spotlight.id.value}", params={"limit": limit}
        ),
        "Hybrid": client.get(
            "/recommendations/hybrid",
            params={"book_id": str(spotlight.id.value), "limit": limit},
        ),
    }
    for name, response in responses.items():
        response.raise_for_status()
        items = response.json()["items"]
        print(f"[{name}]")
        if not items:
            print("  (no recommendations)")
        for item in items:
            book = item["book"]
            print(
                f"  {book['title']} by {book['author']} "
                f"(category={book['category']}) — score={item['score']:.3f}"
            )
        print()


def _print_hybrid_strategy_comparison(
    weighted_engine: RecommendationEngine,
    rrf_engine: RecommendationEngine,
    spotlight: Book,
    user_id: UserId,
    limit: int,
) -> None:
    """Show both pluggable hybrid ranking strategies side by side.

    The REST /recommendations/hybrid endpoint only exposes whichever single
    strategy HYBRID_RANKING_STRATEGY selects, and has no user_id parameter,
    so this calls both RankingStrategy-backed engines directly (Domain/
    Application objects, not HTTP) with a query that has both book_id and
    user_id set -- the only way to see Popularity+Semantic+ALS fused
    together by each strategy in the same run.
    """
    query = RecommendationQuery(limit=limit, book_id=spotlight.id, user_id=user_id)
    print(
        f'Hybrid ranking strategies for: "{spotlight.title.value}" '
        f"(also personalized for demo user '{DEMO_USER_LABEL}')\n"
    )
    for name, engine in (
        ("Hybrid (Weighted Score Fusion)", weighted_engine),
        ("Hybrid (Reciprocal Rank Fusion)", rrf_engine),
    ):
        items = engine.recommend(query).recommendation.items
        print(f"[{name}]")
        if not items:
            print("  (no recommendations)")
        for item in items:
            print(
                f"  {item.book.title.value} by {item.book.author.value} "
                f"(category={item.book.category.value}) — score={item.score:.3f}"
            )
        print()


def _print_evaluation_report(
    context: ApplicationContext,
    books: list[Book],
    als_engine: RecommendationEngine,
    hybrid_weighted_engine: RecommendationEngine,
    hybrid_rrf_engine: RecommendationEngine,
    k: int,
) -> None:
    dataset = _build_evaluation_dataset(books, _user_id(DEMO_USER_LABEL))
    engines: tuple[tuple[str, RecommendationEngine], ...] = (
        ("popularity", context.recommendation_engine),
        ("semantic", context.semantic_recommendation_engine),
        ("als", als_engine),
        ("hybrid_weighted", hybrid_weighted_engine),
        ("hybrid_rrf", hybrid_rrf_engine),
    )
    print(
        f"Offline evaluation (k={k}; ground truth = same-category books relative to each "
        "case's book, personalized for demo user 'alice'; a demo-only heuristic; embeddings "
        "are DeterministicFakeBookEmbeddingGenerator, a placeholder — not a real ML model, so "
        "semantic/hybrid quality here is not representative of a real model):\n"
    )
    print(
        f"{'engine':<18}{'precision@k':>14}{'recall@k':>12}{'map@k':>10}"
        f"{'ndcg@k':>10}{'hit_rate@k':>12}"
    )
    for name, engine in engines:
        result = context.evaluate_recommendation_engine_use_case.execute(engine, name, dataset, k)
        print(
            f"{result.engine_name:<18}{result.precision_at_k:>14.3f}{result.recall_at_k:>12.3f}"
            f"{result.map_at_k:>10.3f}{result.ndcg_at_k:>10.3f}{result.hit_rate_at_k:>12.3f}"
        )


def main(
    argv: list[str] | None = None, *, application_context: ApplicationContext | None = None
) -> int:
    args = _parse_args(argv)
    context = (
        application_context if application_context is not None else ApplicationContext.create()
    )

    books = seed_demo_dataset(context)
    categories = {book.category.value for book in books}
    print(f"Seeded {len(books)} demo books across {len(categories)} categories.\n")

    als_engine = _build_als_engine(context)
    hybrid_weighted_engine, hybrid_rrf_engine = _build_hybrid_engines(context, als_engine)
    demo_user_id = _user_id(DEMO_USER_LABEL)

    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    client = TestClient(app)

    spotlight = books[0]
    _print_recommendation_comparison(client, spotlight, args.limit)
    _print_hybrid_strategy_comparison(
        hybrid_weighted_engine, hybrid_rrf_engine, spotlight, demo_user_id, args.limit
    )
    _print_evaluation_report(
        context, books, als_engine, hybrid_weighted_engine, hybrid_rrf_engine, args.k
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ReadMatch AI recommendation demo end-to-end."
    )
    parser.add_argument(
        "--limit", type=int, default=3, help="Recommendations to show per strategy (default: 3)"
    )
    parser.add_argument(
        "--k", type=int, default=3, help="Top-K for offline evaluation metrics (default: 3)"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
