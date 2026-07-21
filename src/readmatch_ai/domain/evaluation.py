from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class EvaluationCase:
    """One evaluation query and the books considered relevant to it.

    Exactly mirrors RecommendationQuery's optional book_id/user_id split: a
    book-similarity case (Semantic/Hybrid) sets book_id, a personalized case
    (ALS) sets user_id, and a case may set both to evaluate an engine that
    uses either/both. Deliberately decoupled from how relevance was derived
    (category overlap, held-out interactions, curated fixtures) — the
    evaluation pipeline only needs the resulting set.
    """

    relevant_book_ids: frozenset[BookId]
    book_id: BookId | None = None
    user_id: UserId | None = None

    def __post_init__(self) -> None:
        if not self.relevant_book_ids:
            raise ValueError("relevant_book_ids must not be empty")
        if self.book_id is None and self.user_id is None:
            raise ValueError("EvaluationCase requires at least one of book_id or user_id")


@dataclass(frozen=True)
class EvaluationDataset:
    """A deterministic collection of EvaluationCases to evaluate a RecommendationEngine against."""

    cases: tuple[EvaluationCase, ...]

    def __post_init__(self) -> None:
        if not self.cases:
            raise ValueError("cases must not be empty")


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregate ranking-quality metrics for one RecommendationEngine over an EvaluationDataset.

    Each *_at_k field is the mean of that metric across all cases in the
    dataset, so results from different engines (or different k) are directly
    comparable. `coverage` and `novelty_at_k` are None when the caller didn't
    supply the extra evidence they need (catalog_size / popularity data,
    respectively) -- distinguishing "not computed" from a fabricated 0.0.
    """

    engine_name: str
    k: int
    precision_at_k: float
    recall_at_k: float
    map_at_k: float
    ndcg_at_k: float
    hit_rate_at_k: float
    diversity_at_k: float
    case_count: int
    coverage: float | None = None
    novelty_at_k: float | None = None
