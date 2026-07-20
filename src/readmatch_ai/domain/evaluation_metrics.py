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


def _require_positive_k(k: int) -> None:
    if k <= 0:
        raise ValueError(f"k must be positive, got {k!r}")
