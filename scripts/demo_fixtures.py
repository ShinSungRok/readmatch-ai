"""Shared deterministic demo dataset and engine-building helpers.

Used by both scripts/run_demo.py (end-to-end REST walkthrough) and
scripts/generate_quality_report.py (offline recommendation quality
reporting), so there is exactly one deterministic dataset/engine-building
definition, not two independently-maintained copies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
from readmatch_ai.domain.ranking_strategies import (
    ReciprocalRankFusionStrategy,
    WeightedScoreFusionStrategy,
)
from readmatch_ai.domain.recommendation import ALS_SOURCE, POPULARITY_SOURCE, SEMANTIC_SOURCE
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.reranker import DefaultRecommendationReranker
from readmatch_ai.domain.reranking_policies import (
    MMRDiversityPolicy,
    NoveltyBoostPolicy,
    PopularityPenaltyPolicy,
)
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.als_model import train_als_model
from readmatch_ai.infrastructure.als_recommendation_engine import ALSRecommendationEngine
from readmatch_ai.infrastructure.hybrid_recommendation_engine import HybridRecommendationEngine
from readmatch_ai.infrastructure.reranked_recommendation_engine import (
    RerankedRecommendationEngine,
)

# Identifies this fixed, hand-picked dataset in reports/logs -- bump if
# _SEED_BOOKS/_SEED_INTERACTIONS ever change so a stale comparison is
# never silently mistaken for one against the current data.
DATASET_ID = "readmatch-ai-demo-dataset-v1"


@dataclass(frozen=True)
class _SeedBook:
    isbn_12_digits: str
    title: str
    author: str
    category: str
    loan_count: int
    publisher: str
    description: str
    published_date: str


def _isbn13(twelve_digits: str) -> str:
    """Append a valid ISBN-13 check digit to a 12-digit prefix."""
    total = sum((1 if i % 2 == 0 else 3) * int(digit) for i, digit in enumerate(twelve_digits))
    check_digit = (10 - total % 10) % 10
    return twelve_digits + str(check_digit)


# Deterministic, hand-picked across three categories so Popularity (varied
# loan_count) and category-grouping (used below as evaluation ground truth)
# produce visibly different rankings.
SEED_BOOKS: tuple[_SeedBook, ...] = (
    _SeedBook(
        "978000000001",
        "Clean Code",
        "Robert C. Martin",
        "Software Engineering",
        120,
        publisher="Prentice Hall",
        description="A handbook of agile software craftsmanship.",
        published_date="2008-08-01",
    ),
    _SeedBook(
        "978000000002",
        "The Pragmatic Programmer",
        "Andrew Hunt",
        "Software Engineering",
        95,
        publisher="Addison-Wesley",
        description="From journeyman to master, a guide to becoming a better programmer.",
        published_date="1999-10-20",
    ),
    _SeedBook(
        "978000000003",
        "Effective Java",
        "Joshua Bloch",
        "Software Engineering",
        80,
        publisher="Addison-Wesley",
        description="Best practices for the Java platform.",
        published_date="2001-05-01",
    ),
    _SeedBook(
        "978000000004",
        "Dune",
        "Frank Herbert",
        "Science Fiction",
        150,
        publisher="Chilton Books",
        description="A young heir navigates politics, religion, and ecology on a desert planet.",
        published_date="1965-08-01",
    ),
    _SeedBook(
        "978000000005",
        "Foundation",
        "Isaac Asimov",
        "Science Fiction",
        60,
        publisher="Gnome Press",
        description="A mathematician predicts the fall of a galactic empire.",
        published_date="1951-05-01",
    ),
    _SeedBook(
        "978000000006",
        "Neuromancer",
        "William Gibson",
        "Science Fiction",
        40,
        publisher="Ace Books",
        description="A washed-up hacker takes one last job in a near-future dystopia.",
        published_date="1984-07-01",
    ),
    _SeedBook(
        "978000000007",
        "Sapiens",
        "Yuval Noah Harari",
        "History",
        200,
        publisher="Harvill Secker",
        description="A brief history of humankind.",
        published_date="2011-01-01",
    ),
    _SeedBook(
        "978000000008",
        "Guns, Germs, and Steel",
        "Jared Diamond",
        "History",
        30,
        publisher="W. W. Norton",
        description="The fates of human societies, explained by geography and environment.",
        published_date="1997-03-01",
    ),
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
SEED_INTERACTIONS: tuple[_SeedInteraction, ...] = (
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


def user_id(label: str) -> UserId:
    """Deterministic UserId derived from a demo user label, for reproducible output."""
    return UserId(uuid.uuid5(uuid.NAMESPACE_DNS, f"readmatch-ai-demo-user-{label}"))


def _book_id(isbn_12_digits: str) -> BookId:
    """Deterministic BookId derived from a seed book's ISBN prefix.

    RegisterBookUseCase always calls BookId.generate() (a fresh random UUID)
    internally -- correct for real book registration, but it would make
    repeated runs of this deterministic dataset produce different book
    identities each time, which in turn makes tie-break-sensitive results
    (Reciprocal Rank Fusion, MMR diversity -- both sort ties by book id
    string) non-reproducible run to run. seed_demo_dataset constructs Book
    directly instead, bypassing only the id-generation step -- it still
    persists through the same BookRepository.add() the use case itself
    calls, and duplicate-ISBN handling is irrelevant here since every seed
    ISBN is unique by construction.
    """
    return BookId(uuid.uuid5(uuid.NAMESPACE_DNS, f"readmatch-ai-demo-book-{isbn_12_digits}"))


def seed_demo_dataset(context: ApplicationContext) -> list[Book]:
    """Register the demo books/interactions, record popularity, and generate embeddings."""
    books: list[Book] = []
    books_by_isbn_prefix: dict[str, Book] = {}
    for seed in SEED_BOOKS:
        book = Book(
            id=_book_id(seed.isbn_12_digits),
            isbn=ISBN(_isbn13(seed.isbn_12_digits)),
            title=Title(seed.title),
            author=Author(seed.author),
            category=Category(seed.category),
        )
        context.book_repository.add(book)
        context.book_popularity_repository.record(
            BookPopularity(
                book.id,
                loan_count=seed.loan_count,
                period_start="2024-01-01",
                period_end="2024-12-31",
            )
        )
        context.book_metadata_repository.record(
            BookMetadata(
                book.id,
                publisher=seed.publisher,
                description=seed.description,
                published_date=seed.published_date,
            )
        )
        context.generate_book_embedding_use_case.execute(str(book.id.value))
        books.append(book)
        books_by_isbn_prefix[seed.isbn_12_digits] = book

    for interaction in SEED_INTERACTIONS:
        context.user_book_interaction_repository.record(
            UserBookInteraction(
                user_id=user_id(interaction.user_label),
                book_id=books_by_isbn_prefix[interaction.isbn_12_digits].id,
                interaction_count=interaction.interaction_count,
            )
        )
    return books


def build_als_engine(context: ApplicationContext) -> RecommendationEngine:
    """Train ALS fresh from the just-seeded interactions.

    context.als_recommendation_engine was already built (on zero
    interactions) at ApplicationContext.create() time -- ALS trains once,
    eagerly, and does not retroactively reflect interactions recorded
    afterwards (see application_context.py). Callers seed interactions
    after context creation, so this retrains here using the same
    infrastructure building blocks ApplicationContext itself uses.
    """
    model = train_als_model(context.user_book_interaction_repository.list_all())
    return ALSRecommendationEngine(
        model, context.book_repository, context.user_book_interaction_repository
    )


_EQUAL_HYBRID_WEIGHTS = {POPULARITY_SOURCE: 1 / 3, SEMANTIC_SOURCE: 1 / 3, ALS_SOURCE: 1 / 3}


def build_hybrid_engines(
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


def build_reranked_engine(
    context: ApplicationContext, hybrid_engine: RecommendationEngine
) -> RecommendationEngine:
    """Wrap Hybrid (Weighted) with the independent re-ranking stage.

    Reuses the same DefaultRecommendationReranker composition
    ApplicationContext._build_reranker() wires by default (Popularity
    penalty, then Novelty boost, then MMR diversity, in that order) but
    built explicitly around the caller's own hybrid_weighted_engine (not
    context.reranked_recommendation_engine, which wraps
    context.hybrid_recommendation_engine -- whichever single strategy
    HYBRID_RANKING_STRATEGY selects) so this comparison is reproducible
    regardless of that env var.
    """
    reranker = DefaultRecommendationReranker(
        [
            PopularityPenaltyPolicy(context.book_popularity_repository),
            NoveltyBoostPolicy(context.user_book_interaction_repository),
            MMRDiversityPolicy(),
        ]
    )
    return RerankedRecommendationEngine(hybrid_engine, reranker)


def build_comparison_engines(
    context: ApplicationContext,
) -> tuple[tuple[str, RecommendationEngine], ...]:
    """Build the standard 6-engine comparison set: Popularity, Semantic, ALS,
    Hybrid (Weighted), Hybrid (RRF), Hybrid + Re-ranking -- in that order,
    which also fixes tie-break precedence for any consumer that ranks
    engines by input order (see GenerateRecommendationQualityReportUseCase).
    """
    als_engine = build_als_engine(context)
    hybrid_weighted_engine, hybrid_rrf_engine = build_hybrid_engines(context, als_engine)
    reranked_engine = build_reranked_engine(context, hybrid_weighted_engine)
    return (
        ("popularity", context.recommendation_engine),
        ("semantic", context.semantic_recommendation_engine),
        ("als", als_engine),
        ("hybrid_weighted", hybrid_weighted_engine),
        ("hybrid_rrf", hybrid_rrf_engine),
        ("hybrid_reranked", reranked_engine),
    )


def build_evaluation_dataset(books: list[Book], user: UserId) -> EvaluationDataset:
    """Ground truth for this deterministic dataset only: books in the same
    category are 'relevant'.

    This is a policy choice local to this fixture, not part of the
    Evaluation domain itself (EvaluationCase.relevant_book_ids is
    deliberately source-agnostic) -- a real ground-truth source is a future
    concern.

    Every case carries the same demo user_id alongside its book_id, so one
    dataset exercises Popularity, Semantic, ALS, and Hybrid uniformly --
    Hybrid needs both fields present to query all three sub-engines. Reusing
    one fixed user across every case is a demo-only simplification, not a
    real per-case personalization design.
    """
    cases = [
        EvaluationCase(
            book_id=book.id,
            user_id=user,
            relevant_book_ids=frozenset(
                other.id
                for other in books
                if other.category == book.category and other.id != book.id
            ),
        )
        for book in books
    ]
    return EvaluationDataset(cases=tuple(case for case in cases if case.relevant_book_ids))
