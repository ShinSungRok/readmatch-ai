from __future__ import annotations

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.ranking_strategy import RankingCandidateList, RankingStrategy
from readmatch_ai.domain.recommendation import HYBRID_SOURCE, RecommendationItem

_DEFAULT_RRF_K = 60


class WeightedScoreFusionStrategy(RankingStrategy):
    """Min-max normalizes each source's scores independently, then combines via a weighted sum.

    A book appearing in multiple sources is merged into one item whose score
    is the full weighted-sum combination of every source's (normalized)
    contribution, not just the highest single source. Weights are
    renormalized across whichever sources actually produced candidates for
    a given call (e.g. Semantic/ALS contribute nothing without a book_id/
    user_id) so the combined score isn't silently scaled down just because
    a source wasn't queryable this time — matching ADR-004's "Popularity is
    the baseline and cold-start fallback" generalized to any number of
    sources, not just a hardcoded Popularity/Semantic pair.
    """

    def __init__(self, weights: dict[str, float]) -> None:
        if any(weight < 0 for weight in weights.values()):
            raise ValueError("weights must be non-negative")
        self._weights = weights

    def fuse(
        self, candidate_lists: list[RankingCandidateList], limit: int
    ) -> list[RecommendationItem]:
        active_lists = [
            candidate_list for candidate_list in candidate_lists if candidate_list.items
        ]
        if not active_lists:
            return []

        effective_weights = self._effective_weights(active_lists)
        books: dict[BookId, Book] = {}
        combined_scores: dict[BookId, float] = {}
        contributing_sources: dict[BookId, set[str]] = {}
        for candidate_list in active_lists:
            weight = effective_weights[candidate_list.source]
            normalized = _min_max_normalize(candidate_list.items)
            for item in candidate_list.items:
                books[item.book.id] = item.book
                combined_scores[item.book.id] = (
                    combined_scores.get(item.book.id, 0.0) + weight * normalized[item.book.id]
                )
                contributing_sources.setdefault(item.book.id, set()).add(candidate_list.source)

        return _rank_and_truncate(books, combined_scores, contributing_sources, limit)

    def _effective_weights(self, active_lists: list[RankingCandidateList]) -> dict[str, float]:
        total_weight = sum(self._weights.get(cl.source, 0.0) for cl in active_lists)
        if total_weight == 0.0:
            # None of the active sources has a configured weight: split
            # evenly rather than collapsing every score to zero.
            return {cl.source: 1.0 / len(active_lists) for cl in active_lists}
        return {cl.source: self._weights.get(cl.source, 0.0) / total_weight for cl in active_lists}


class ReciprocalRankFusionStrategy(RankingStrategy):
    """Combines rankings using Reciprocal Rank Fusion: score = sum(1 / (k + rank)).

    Rank-based, not score-based — ignores each source's raw scores
    entirely, so sources with very different, non-comparable score scales
    (raw loan_count vs. cosine similarity vs. ALS factor dot-product)
    combine meaningfully with no per-source normalization or weighting
    needed.
    """

    def __init__(self, k: int = _DEFAULT_RRF_K) -> None:
        if k <= 0:
            raise ValueError("k must be positive")
        self._k = k

    def fuse(
        self, candidate_lists: list[RankingCandidateList], limit: int
    ) -> list[RecommendationItem]:
        books: dict[BookId, Book] = {}
        combined_scores: dict[BookId, float] = {}
        contributing_sources: dict[BookId, set[str]] = {}
        for candidate_list in candidate_lists:
            for rank, item in enumerate(candidate_list.items, start=1):
                books[item.book.id] = item.book
                combined_scores[item.book.id] = combined_scores.get(item.book.id, 0.0) + 1.0 / (
                    self._k + rank
                )
                contributing_sources.setdefault(item.book.id, set()).add(candidate_list.source)

        return _rank_and_truncate(books, combined_scores, contributing_sources, limit)


def _min_max_normalize(items: list[RecommendationItem]) -> dict[BookId, float]:
    scores = [item.score for item in items]
    minimum, maximum = min(scores), max(scores)
    if minimum == maximum:
        return {item.book.id: 1.0 for item in items}
    return {item.book.id: (item.score - minimum) / (maximum - minimum) for item in items}


def _rank_and_truncate(
    books: dict[BookId, Book],
    scores: dict[BookId, float],
    contributing_sources: dict[BookId, set[str]],
    limit: int,
) -> list[RecommendationItem]:
    # Deterministic tiebreak (by id) so equal-score books always sort the
    # same way, regardless of dict/insertion order.
    ranked_book_ids = sorted(scores, key=lambda book_id: (-scores[book_id], str(book_id.value)))[
        :limit
    ]
    return [
        RecommendationItem(
            book=books[book_id],
            score=scores[book_id],
            source=HYBRID_SOURCE,
            contributing_sources=frozenset(contributing_sources[book_id]),
        )
        for book_id in ranked_book_ids
    ]
