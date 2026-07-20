#!/usr/bin/env python3
"""End-to-end recommendation demo: seeds a deterministic dataset, exercises the
Popularity, Semantic, and Hybrid recommendation REST endpoints, and reports
offline evaluation metrics for all three engines.

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
from dataclasses import dataclass

from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


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


def seed_demo_dataset(context: ApplicationContext) -> list[Book]:
    """Register the demo books, record their popularity, and generate their embeddings."""
    books: list[Book] = []
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
    return books


def _build_evaluation_dataset(books: list[Book]) -> EvaluationDataset:
    """Ground truth for this demo only: books in the same category are 'relevant'.

    This is a policy choice local to the demo script, not part of the
    Evaluation domain itself (EvaluationCase.relevant_book_ids is deliberately
    source-agnostic) -- a real ground-truth source is a future concern.
    """
    cases = [
        EvaluationCase(
            book_id=book.id,
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


def _print_evaluation_report(context: ApplicationContext, books: list[Book], k: int) -> None:
    dataset = _build_evaluation_dataset(books)
    engines: tuple[tuple[str, RecommendationEngine], ...] = (
        ("popularity", context.recommendation_engine),
        ("semantic", context.semantic_recommendation_engine),
        ("hybrid", context.hybrid_recommendation_engine),
    )
    print(
        f"Offline evaluation (k={k}; ground truth = same-category books, a demo-only "
        "heuristic; embeddings are DeterministicFakeBookEmbeddingGenerator, a "
        "placeholder — not a real ML model, so semantic/hybrid quality here is not "
        "representative of a real model):\n"
    )
    print(f"{'engine':<12}{'precision@k':>14}{'recall@k':>12}{'map@k':>10}{'ndcg@k':>10}{'hit_rate@k':>12}")
    for name, engine in engines:
        result = context.evaluate_recommendation_engine_use_case.execute(engine, name, dataset, k)
        print(
            f"{result.engine_name:<12}{result.precision_at_k:>14.3f}{result.recall_at_k:>12.3f}"
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

    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    client = TestClient(app)

    spotlight = books[0]
    _print_recommendation_comparison(client, spotlight, args.limit)
    _print_evaluation_report(context, books, args.k)
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
