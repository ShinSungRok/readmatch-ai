from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

from readmatch_ai.domain.book import BookId


def precision_at_k(recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
    """Fraction of the top-k recommendations that are relevant.

    Divides by k (not by however many were actually recommended), so a
    short result list is penalized rather than scored as if k were smaller.
    """
    _require_positive_k(k)
    top_k = recommended[:k]
    hits = sum(1 for book_id in top_k if book_id in relevant)
    return hits / k


def recall_at_k(recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
    """Fraction of all relevant books that appear in the top-k recommendations."""
    _require_positive_k(k)
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for book_id in top_k if book_id in relevant)
    return hits / len(relevant)


def average_precision_at_k(
    recommended: Sequence[BookId], relevant: frozenset[BookId], k: int
) -> float:
    """Average Precision@k: rewards relevant books appearing earlier in the ranking."""
    _require_positive_k(k)
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    hits = 0
    score = 0.0
    for rank, book_id in enumerate(top_k, start=1):
        if book_id in relevant:
            hits += 1
            score += hits / rank
    return score / min(len(relevant), k)


def ndcg_at_k(recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
    """Normalized Discounted Cumulative Gain@k, using binary relevance."""
    _require_positive_k(k)
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, book_id in enumerate(top_k, start=1)
        if book_id in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def hit_rate_at_k(recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
    """1.0 if at least one relevant book appears in the top-k, else 0.0.

    Meant to be averaged across an EvaluationDataset's cases by the caller,
    yielding the standard "fraction of queries with at least one hit".
    """
    _require_positive_k(k)
    top_k = recommended[:k]
    return 1.0 if any(book_id in relevant for book_id in top_k) else 0.0


def diversity_at_k(categories: Sequence[str], k: int) -> float:
    """Fraction of distinct categories among the top-k recommendations.

    Relevance-independent (no `relevant` argument): unlike the ranking
    metrics above, diversity measures a property of the recommended list
    itself, not agreement with ground truth -- the dimension re-ranking
    policies like MMRDiversityPolicy exist to improve. Categories are used
    as this project's existing similarity proxy (see
    MMRDiversityPolicy / the demo's evaluation ground truth) rather than
    introducing an embedding-based dependency into an otherwise
    dependency-free metric function. 1.0 means every one of the top-k items
    belongs to a different category (maximally diverse); a low score means
    the list is dominated by one or few categories. Divides by the actual
    number of recommendations returned (not by k), since this metric
    describes the returned list's own internal composition rather than
    penalizing a short list the way precision_at_k deliberately does.
    """
    _require_positive_k(k)
    top_k = categories[:k]
    if not top_k:
        return 0.0
    return len(set(top_k)) / len(top_k)


def catalog_coverage(recommended_book_ids: Iterable[BookId], catalog_size: int) -> float:
    """Fraction of the catalog reached by the union of recommendations across a whole run.

    Unlike the per-case *_at_k metrics above, coverage is a run-level
    aggregate: the caller passes every book_id recommended across every
    evaluation case (duplicates -- the same book recommended for multiple
    cases -- collapse naturally via `set()`, so covering the same book
    repeatedly doesn't inflate the score). `catalog_size` must be positive
    (the total number of books an engine could possibly recommend); an
    empty `recommended_book_ids` yields 0.0, never a division error.
    """
    if catalog_size <= 0:
        raise ValueError(f"catalog_size must be positive, got {catalog_size!r}")
    distinct_book_ids = set(recommended_book_ids)
    return len(distinct_book_ids) / catalog_size


def novelty_at_k(
    popularity_counts: Sequence[int], catalog_total_popularity: int, k: int
) -> float | None:
    """Mean self-information novelty of the top-k recommendations.

    For each recommended book with a recorded popularity count `c`, its
    novelty is `-log2(c / catalog_total_popularity)` (Zhou et al.'s
    self-information novelty: rarer/less-popular books score higher,
    popular books score near zero). Averaged across the top-k books that
    *have* popularity evidence; books with no recorded popularity (count of
    0, e.g. never loaned) are excluded from the average rather than
    fabricating a value for them via an undefined log(0).

    Returns None -- not 0.0 -- when there is no popularity evidence to
    compute from at all (an empty/all-zero top-k, or a catalog with no
    recorded popularity), distinguishing "not novel" from "cannot be
    measured", per this Sprint's "Novelty where sufficient popularity ...
    evidence exists".
    """
    _require_positive_k(k)
    if catalog_total_popularity <= 0:
        return None
    top_k_with_evidence = [count for count in popularity_counts[:k] if count > 0]
    if not top_k_with_evidence:
        return None
    return sum(
        -math.log2(count / catalog_total_popularity) for count in top_k_with_evidence
    ) / len(top_k_with_evidence)


def _require_positive_k(k: int) -> None:
    if k <= 0:
        raise ValueError(f"k must be positive, got {k!r}")


class RecommendationMetric(ABC):
    """Independent, named Top-K ranking metric, usable polymorphically.

    Each concrete metric below wraps exactly one of this module's existing
    pure functions -- never reimplements a calculation -- so there remains
    exactly one source of truth per metric. This class only adds a
    uniform `name`/`compute()` surface a caller can iterate over generically
    (e.g. "run every metric in this list against this case's recommended
    list"), which the plain functions above don't provide on their own;
    EvaluateRecommendationEngineUseCase is unaffected and continues calling
    the functions directly, since it has no such need for polymorphism.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """This metric's stable identifier (matches EvaluationResult's field names)."""

    @abstractmethod
    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        """Compute this metric's value for one case's recommended list against its relevant set."""


class PrecisionAtK(RecommendationMetric):
    @property
    def name(self) -> str:
        return "precision_at_k"

    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        return precision_at_k(recommended, relevant, k)


class RecallAtK(RecommendationMetric):
    @property
    def name(self) -> str:
        return "recall_at_k"

    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        return recall_at_k(recommended, relevant, k)


class HitRateAtK(RecommendationMetric):
    @property
    def name(self) -> str:
        return "hit_rate_at_k"

    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        return hit_rate_at_k(recommended, relevant, k)


class MeanAveragePrecisionAtK(RecommendationMetric):
    @property
    def name(self) -> str:
        return "map_at_k"

    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        return average_precision_at_k(recommended, relevant, k)


class NdcgAtK(RecommendationMetric):
    @property
    def name(self) -> str:
        return "ndcg_at_k"

    def compute(self, recommended: Sequence[BookId], relevant: frozenset[BookId], k: int) -> float:
        return ndcg_at_k(recommended, relevant, k)


# Fixed, deterministic order -- mirrors generate_recommendation_quality_report_use_case's
# own _METRIC_NAMES ordering for the metrics it shares, independent of
# instantiation/dict order.
STANDARD_METRICS: tuple[RecommendationMetric, ...] = (
    PrecisionAtK(),
    RecallAtK(),
    MeanAveragePrecisionAtK(),
    NdcgAtK(),
    HitRateAtK(),
)
