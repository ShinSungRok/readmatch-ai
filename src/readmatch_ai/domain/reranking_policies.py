from __future__ import annotations

from collections.abc import Callable

from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.book_popularity import BookPopularityRepository
from readmatch_ai.domain.recommendation import RecommendationItem
from readmatch_ai.domain.reranker import RerankingContext, RerankingPolicy
from readmatch_ai.domain.user_book_interaction_repository import UserBookInteractionRepository

_DEFAULT_MMR_LAMBDA = 0.5
_DEFAULT_NOVELTY_BOOST = 0.1
_DEFAULT_POPULARITY_PENALTY = 0.3


def _same_category_similarity(a: Book, b: Book) -> float:
    return 1.0 if a.category == b.category else 0.0


class MMRDiversityPolicy(RerankingPolicy):
    """Maximal Marginal Relevance-style diversification.

    Iteratively selects the item that best balances its own (min-max
    normalized) relevance score against similarity to items already
    selected, instead of purely sorting by score -- so near-duplicate
    candidates don't crowd out otherwise-relevant variety. Similarity
    defaults to a category-overlap proxy: Book carries no embedding vector
    here, keeping this policy free of any Infrastructure/embedding
    dependency, consistent with how the rest of the codebase already uses
    category as a similarity/relevance proxy (ranking_strategies.py's
    fusion tie-breaks; the demo's evaluation ground truth). A different
    similarity function can be injected without changing this policy's
    selection logic.
    """

    def __init__(
        self,
        lambda_param: float = _DEFAULT_MMR_LAMBDA,
        similarity: Callable[[Book, Book], float] = _same_category_similarity,
    ) -> None:
        if not 0.0 <= lambda_param <= 1.0:
            raise ValueError(f"lambda_param must be within [0, 1], got {lambda_param!r}")
        self._lambda = lambda_param
        self._similarity = similarity

    def apply(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        if not items:
            return []
        normalized = _min_max_normalize(items)
        remaining = list(items)
        selected: list[RecommendationItem] = []
        while remaining and len(selected) < limit:
            best = self._select_next(remaining, selected, normalized)
            selected.append(best)
            remaining.remove(best)
        return selected

    def _select_next(
        self,
        remaining: list[RecommendationItem],
        selected: list[RecommendationItem],
        normalized: dict[BookId, float],
    ) -> RecommendationItem:
        scored = [(self._mmr_score(item, selected, normalized), item) for item in remaining]
        best_score = max(score for score, _ in scored)
        # Deterministic tiebreak (by id), matching ranking_strategies.py's convention.
        return min(
            (item for score, item in scored if score == best_score),
            key=lambda item: str(item.book.id.value),
        )

    def _mmr_score(
        self,
        item: RecommendationItem,
        selected: list[RecommendationItem],
        normalized: dict[BookId, float],
    ) -> float:
        relevance = normalized[item.book.id]
        if not selected:
            return relevance
        max_similarity = max(self._similarity(item.book, other.book) for other in selected)
        return self._lambda * relevance - (1.0 - self._lambda) * max_similarity


class NoveltyBoostPolicy(RerankingPolicy):
    """Boosts items the context's user has not already interacted with.

    Complements ALS (which already excludes a user's own interacted books
    from its own candidates) by rewarding under-exposure for *every*
    source -- Popularity/Semantic candidates have no knowledge of a
    specific user's history at all. A no-op (returns items unchanged) when
    no user_id is present in the context, since novelty-to-a-user is
    undefined without a user.
    """

    def __init__(
        self,
        interaction_repository: UserBookInteractionRepository,
        boost: float = _DEFAULT_NOVELTY_BOOST,
    ) -> None:
        if boost < 0.0:
            raise ValueError(f"boost must be non-negative, got {boost!r}")
        self._interaction_repository = interaction_repository
        self._boost = boost

    def apply(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        if context.user_id is None or not items:
            return items
        known_book_ids = {
            interaction.book_id
            for interaction in self._interaction_repository.list_by_user(context.user_id)
        }
        boosted = [
            _with_score(
                item, item.score + self._boost if item.book.id not in known_book_ids else item.score
            )
            for item in items
        ]
        return _sorted_by_score_desc(boosted)


class PopularityPenaltyPolicy(RerankingPolicy):
    """Penalizes items with a high global loan_count, damping over-exposure of popular books.

    Multiplies each item's score by `(1 - penalty * normalized_loan_count)`,
    where normalized_loan_count is min-max normalized across exactly this
    call's candidate items (not the whole catalog) -- consistent with how
    WeightedScoreFusionStrategy normalizes per-call, not globally. A book
    with no recorded popularity signal is treated as loan_count=0. If
    *every* candidate has loan_count=0 (no popularity signal at all for
    this call), no penalty is applied to anyone -- deliberately not reusing
    the "all-equal collapses to 1.0" min-max convention here, since that
    would penalize every item at full strength precisely when there is no
    popularity signal to justify penalizing any of them.
    """

    def __init__(
        self,
        popularity_repository: BookPopularityRepository,
        penalty: float = _DEFAULT_POPULARITY_PENALTY,
    ) -> None:
        if not 0.0 <= penalty <= 1.0:
            raise ValueError(f"penalty must be within [0, 1], got {penalty!r}")
        self._popularity_repository = popularity_repository
        self._penalty = penalty

    def apply(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        if not items:
            return []
        loan_counts = {item.book.id: float(self._loan_count(item.book.id)) for item in items}
        if max(loan_counts.values()) == 0.0:
            return _sorted_by_score_desc(items)
        normalized = _min_max_normalize_values(loan_counts)
        penalized = [
            _with_score(item, item.score * (1.0 - self._penalty * normalized[item.book.id]))
            for item in items
        ]
        return _sorted_by_score_desc(penalized)

    def _loan_count(self, book_id: BookId) -> int:
        popularity = self._popularity_repository.get_by_book_id(book_id)
        return popularity.loan_count if popularity is not None else 0


def _with_score(item: RecommendationItem, score: float) -> RecommendationItem:
    return RecommendationItem(
        book=item.book,
        score=score,
        source=item.source,
        contributing_sources=item.contributing_sources,
    )


def _sorted_by_score_desc(items: list[RecommendationItem]) -> list[RecommendationItem]:
    # Deterministic tiebreak (by id), matching ranking_strategies.py's convention.
    return sorted(items, key=lambda item: (-item.score, str(item.book.id.value)))


def _min_max_normalize(items: list[RecommendationItem]) -> dict[BookId, float]:
    return _min_max_normalize_values({item.book.id: item.score for item in items})


def _min_max_normalize_values(values: dict[BookId, float]) -> dict[BookId, float]:
    minimum, maximum = min(values.values()), max(values.values())
    if minimum == maximum:
        return dict.fromkeys(values, 1.0)
    return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}
