#!/usr/bin/env python3
"""End-to-end recommendation demo: seeds a deterministic dataset, exercises the
Popularity, Semantic, Hybrid, and Personalized (Hybrid + re-ranking)
recommendation REST endpoints, and reports offline evaluation metrics
comparing Popularity, Semantic, ALS, both Hybrid ranking strategies (Weighted
Score Fusion and Reciprocal Rank Fusion), and Hybrid with the re-ranking
stage (diversity, novelty, popularity-penalty policies) applied on top.

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

from demo_fixtures import (
    DEMO_USER_LABEL,
    build_als_engine,
    build_evaluation_dataset,
    build_hybrid_engines,
    build_reranked_engine,
    seed_demo_dataset,
)
from demo_fixtures import user_id as _user_id
from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


def _print_recommendation_comparison(
    client: TestClient, spotlight: Book, user_id: UserId, limit: int
) -> None:
    """Popularity/Semantic/Hybrid/Personalized, all via the real REST API.

    Personalized (GET /recommendations/personalized/{user_id}) routes
    through RecommendationEngine -> Hybrid ranking -> RecommendationReranker
    exactly as the API layer does for a real client -- this Sprint's
    "invoke the personalized REST endpoint rather than calling the
    personalized engine directly where practical". Hybrid is also called
    with user_id here so its ALS signal is active for the comparison, same
    as Personalized.
    """
    print(
        f'Recommendations similar to: "{spotlight.title.value}" by '
        f"{spotlight.author.value} ({spotlight.category.value}), "
        f"personalized for demo user '{DEMO_USER_LABEL}'\n"
    )
    responses = {
        "Popularity": client.get("/recommendations/popularity", params={"limit": limit}),
        "Semantic": client.get(
            f"/recommendations/semantic/{spotlight.id.value}", params={"limit": limit}
        ),
        "Hybrid": client.get(
            "/recommendations/hybrid",
            params={
                "book_id": str(spotlight.id.value),
                "user_id": str(user_id.value),
                "limit": limit,
            },
        ),
        "Personalized (Hybrid + Re-ranking)": client.get(
            f"/recommendations/personalized/{user_id.value}",
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


def _print_explained_recommendations(
    client: TestClient, spotlight: Book, user_id: UserId, limit: int
) -> None:
    """Personalized recommendations plus structured explanation reasons, via
    the real REST API (GET /recommendations/personalized/{user_id}/explained).

    Reasons communicate observable signals and system rationale -- they are
    not mathematical proof that a single signal alone caused a ranking
    position (see README's Explainable Recommendations section). An item
    may print with no reasons at all when evidence is limited.
    """
    print(
        f"Explained personalized recommendations for demo user '{DEMO_USER_LABEL}', similar to: "
        f'"{spotlight.title.value}"\n'
    )
    response = client.get(
        f"/recommendations/personalized/{user_id.value}/explained",
        params={"book_id": str(spotlight.id.value), "limit": limit},
    )
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        print("  (no recommendations)")
    for item in items:
        book = item["book"]
        print(
            f"  {book['title']} by {book['author']} "
            f"(category={book['category']}) — score={item['score']:.3f}"
        )
        if not item["reasons"]:
            print("    (no supporting reasons)")
        for reason in item["reasons"]:
            print(f"    - [{reason['type']}] {reason['message']}")
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
    reranked_engine: RecommendationEngine,
    k: int,
) -> None:
    dataset = build_evaluation_dataset(books, _user_id(DEMO_USER_LABEL))
    engines: tuple[tuple[str, RecommendationEngine], ...] = (
        ("popularity", context.recommendation_engine),
        ("semantic", context.semantic_recommendation_engine),
        ("als", als_engine),
        ("hybrid_weighted", hybrid_weighted_engine),
        ("hybrid_rrf", hybrid_rrf_engine),
        ("hybrid_reranked", reranked_engine),
    )
    print(
        f"Offline evaluation (k={k}; ground truth = same-category books relative to each "
        "case's book, personalized for demo user 'alice'; a demo-only heuristic; embeddings "
        "are DeterministicFakeBookEmbeddingGenerator, a placeholder — not a real ML model, so "
        "semantic/hybrid quality here is not representative of a real model; diversity@k is "
        "relevance-independent and measures the recommended list's own category spread):\n"
    )
    print(
        f"{'engine':<18}{'precision@k':>14}{'recall@k':>12}{'map@k':>10}"
        f"{'ndcg@k':>10}{'hit_rate@k':>12}{'diversity@k':>14}"
    )
    for name, engine in engines:
        result = context.evaluate_recommendation_engine_use_case.execute(engine, name, dataset, k)
        print(
            f"{result.engine_name:<18}{result.precision_at_k:>14.3f}{result.recall_at_k:>12.3f}"
            f"{result.map_at_k:>10.3f}{result.ndcg_at_k:>10.3f}{result.hit_rate_at_k:>12.3f}"
            f"{result.diversity_at_k:>14.3f}"
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

    als_engine = build_als_engine(context)
    hybrid_weighted_engine, hybrid_rrf_engine = build_hybrid_engines(context, als_engine)
    reranked_engine = build_reranked_engine(context, hybrid_weighted_engine)
    demo_user_id = _user_id(DEMO_USER_LABEL)

    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    client = TestClient(app)

    spotlight = books[0]
    _print_recommendation_comparison(client, spotlight, demo_user_id, args.limit)
    _print_explained_recommendations(client, spotlight, demo_user_id, args.limit)
    _print_hybrid_strategy_comparison(
        hybrid_weighted_engine, hybrid_rrf_engine, spotlight, demo_user_id, args.limit
    )
    _print_evaluation_report(
        context,
        books,
        als_engine,
        hybrid_weighted_engine,
        hybrid_rrf_engine,
        reranked_engine,
        args.k,
    )
    print(
        "\nFor a structured, exportable (Markdown/CSV) version of this comparison, plus "
        "coverage/novelty metrics and a CI-suitable regression check, see:\n"
        "  python scripts/generate_quality_report.py"
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
