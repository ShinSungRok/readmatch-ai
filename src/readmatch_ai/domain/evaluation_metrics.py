from __future__ import annotations

import math
from collections.abc import Sequence

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


def _require_positive_k(k: int) -> None:
    if k <= 0:
        raise ValueError(f"k must be positive, got {k!r}")
