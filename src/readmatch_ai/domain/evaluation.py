from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class EvaluationCase:
    """One evaluation query: a source book and the books considered relevant to it.

    Deliberately decoupled from how relevance was derived (category overlap,
    curated fixtures, or a future user-interaction signal) — the evaluation
    pipeline only needs the resulting set.
    """

    book_id: BookId
    relevant_book_ids: frozenset[BookId]

    def __post_init__(self) -> None:
        if not self.relevant_book_ids:
            raise ValueError("relevant_book_ids must not be empty")


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
    comparable.
    """

    engine_name: str
    k: int
    precision_at_k: float
    recall_at_k: float
    map_at_k: float
    ndcg_at_k: float
    hit_rate_at_k: float
    case_count: int
