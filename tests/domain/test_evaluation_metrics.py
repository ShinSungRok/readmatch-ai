import math
from collections.abc import Callable, Sequence

import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation_metrics import (
    average_precision_at_k,
    diversity_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

A, B, C, X, Y, Z = (BookId.generate() for _ in range(6))

_RankingMetric = Callable[[Sequence[BookId], frozenset[BookId], int], float]


@pytest.mark.parametrize("metric", [precision_at_k, recall_at_k, average_precision_at_k, ndcg_at_k])
def test_metrics_reject_non_positive_k(metric: _RankingMetric) -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        metric([A], frozenset({A}), 0)


def test_hit_rate_at_k_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        hit_rate_at_k([A], frozenset({A}), 0)


def test_precision_at_k_counts_hits_within_top_k() -> None:
    relevant = frozenset({A, B})
    recommended = [A, X, B, Y, Z]

    assert precision_at_k(recommended, relevant, k=5) == pytest.approx(2 / 5)


def test_precision_at_k_truncates_to_k() -> None:
    relevant = frozenset({A, B})
    recommended = [A, X, B, Y, Z]

    assert precision_at_k(recommended, relevant, k=2) == pytest.approx(1 / 2)


def test_precision_at_k_divides_by_k_not_by_result_length() -> None:
    relevant = frozenset({A})
    recommended = [A]

    assert precision_at_k(recommended, relevant, k=5) == pytest.approx(1 / 5)


def test_precision_at_k_returns_zero_when_no_hits() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, Z]

    assert precision_at_k(recommended, relevant, k=3) == 0.0


def test_recall_at_k_counts_hits_over_all_relevant() -> None:
    relevant = frozenset({A, B, C})
    recommended = [A, X, B]

    assert recall_at_k(recommended, relevant, k=3) == pytest.approx(2 / 3)


def test_recall_at_k_returns_zero_for_empty_relevant() -> None:
    assert recall_at_k([A], frozenset(), k=3) == 0.0


def test_average_precision_at_k_rewards_earlier_hits() -> None:
    relevant = frozenset({A, B, C})
    recommended = [A, X, B, Y, C]

    expected = (1 / 1 + 2 / 3 + 3 / 5) / 3
    assert average_precision_at_k(recommended, relevant, k=5) == pytest.approx(expected)


def test_average_precision_at_k_is_one_for_a_perfect_ranking() -> None:
    relevant = frozenset({A, B})
    recommended = [A, B]

    assert average_precision_at_k(recommended, relevant, k=2) == pytest.approx(1.0)


def test_average_precision_at_k_returns_zero_when_no_hits() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, Z]

    assert average_precision_at_k(recommended, relevant, k=3) == 0.0


def test_average_precision_at_k_returns_zero_for_empty_relevant() -> None:
    assert average_precision_at_k([A], frozenset(), k=3) == 0.0


def test_ndcg_at_k_matches_hand_computed_gain() -> None:
    relevant = frozenset({A, B, C})
    recommended = [A, X, B, Y, C]

    dcg = 1.0 / math.log2(2) + 1.0 / math.log2(4) + 1.0 / math.log2(6)
    idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3) + 1.0 / math.log2(4)
    assert ndcg_at_k(recommended, relevant, k=5) == pytest.approx(dcg / idcg)


def test_ndcg_at_k_is_one_for_a_perfect_ranking() -> None:
    relevant = frozenset({A, B})
    recommended = [A, B]

    assert ndcg_at_k(recommended, relevant, k=2) == pytest.approx(1.0)


def test_ndcg_at_k_returns_zero_when_no_hits() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, Z]

    assert ndcg_at_k(recommended, relevant, k=3) == 0.0


def test_ndcg_at_k_returns_zero_for_empty_relevant() -> None:
    assert ndcg_at_k([A], frozenset(), k=3) == 0.0


def test_hit_rate_at_k_is_one_when_any_hit_present() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, A]

    assert hit_rate_at_k(recommended, relevant, k=3) == 1.0


def test_hit_rate_at_k_is_zero_when_no_hit_present() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, Z]

    assert hit_rate_at_k(recommended, relevant, k=3) == 0.0


def test_hit_rate_at_k_ignores_hits_beyond_k() -> None:
    relevant = frozenset({A})
    recommended = [X, Y, A]

    assert hit_rate_at_k(recommended, relevant, k=2) == 0.0


def test_diversity_at_k_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        diversity_at_k(["Fiction"], 0)


def test_diversity_at_k_is_one_when_every_category_is_distinct() -> None:
    assert diversity_at_k(["Fiction", "History", "Science"], k=3) == pytest.approx(1.0)


def test_diversity_at_k_is_low_when_categories_repeat() -> None:
    assert diversity_at_k(["Fiction", "Fiction", "Fiction"], k=3) == pytest.approx(1 / 3)


def test_diversity_at_k_truncates_to_k() -> None:
    assert diversity_at_k(["Fiction", "History", "Science"], k=2) == pytest.approx(1.0)


def test_diversity_at_k_returns_zero_for_an_empty_list() -> None:
    assert diversity_at_k([], k=3) == 0.0
