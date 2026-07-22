import math
from collections.abc import Callable, Sequence

import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation_metrics import (
    STANDARD_METRICS,
    HitRateAtK,
    MeanAveragePrecisionAtK,
    NdcgAtK,
    PrecisionAtK,
    RecallAtK,
    average_precision_at_k,
    catalog_coverage,
    diversity_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    novelty_at_k,
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


# --- catalog_coverage ---


def test_catalog_coverage_rejects_non_positive_catalog_size() -> None:
    with pytest.raises(ValueError, match="catalog_size"):
        catalog_coverage([A], 0)


def test_catalog_coverage_is_the_fraction_of_distinct_books_recommended() -> None:
    assert catalog_coverage([A, B], catalog_size=4) == pytest.approx(0.5)


def test_catalog_coverage_deduplicates_repeated_book_ids() -> None:
    # The same book recommended across multiple cases must not inflate coverage.
    assert catalog_coverage([A, A, A, B], catalog_size=4) == pytest.approx(0.5)


def test_catalog_coverage_returns_zero_for_no_recommendations() -> None:
    assert catalog_coverage([], catalog_size=10) == 0.0


def test_catalog_coverage_is_one_when_the_entire_catalog_is_covered() -> None:
    assert catalog_coverage([A, B], catalog_size=2) == pytest.approx(1.0)


# --- novelty_at_k ---


def test_novelty_at_k_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        novelty_at_k([10], catalog_total_popularity=100, k=0)


def test_novelty_at_k_returns_none_when_catalog_has_no_popularity_evidence() -> None:
    assert novelty_at_k([10, 20], catalog_total_popularity=0, k=2) is None


def test_novelty_at_k_returns_none_for_an_empty_recommendation_list() -> None:
    assert novelty_at_k([], catalog_total_popularity=100, k=3) is None


def test_novelty_at_k_returns_none_when_no_recommended_item_has_popularity_evidence() -> None:
    assert novelty_at_k([0, 0, 0], catalog_total_popularity=100, k=3) is None


def test_novelty_at_k_excludes_zero_count_items_from_the_average() -> None:
    # 0-count items (no recorded popularity) are skipped rather than
    # fabricating a value via the undefined log2(0).
    with_zero = novelty_at_k([10, 0], catalog_total_popularity=100, k=2)
    without_zero = novelty_at_k([10], catalog_total_popularity=100, k=1)
    assert with_zero == pytest.approx(without_zero)


def test_novelty_at_k_scores_rarer_items_higher() -> None:
    rare = novelty_at_k([1], catalog_total_popularity=1000, k=1)
    common = novelty_at_k([500], catalog_total_popularity=1000, k=1)
    assert rare is not None and common is not None
    assert rare > common


def test_novelty_at_k_matches_hand_computed_self_information() -> None:
    expected = (-math.log2(10 / 100) + -math.log2(20 / 100)) / 2
    assert novelty_at_k([10, 20], catalog_total_popularity=100, k=2) == pytest.approx(expected)


def test_novelty_at_k_truncates_to_k() -> None:
    assert novelty_at_k([10, 20, 30], catalog_total_popularity=100, k=1) == pytest.approx(
        novelty_at_k([10], catalog_total_popularity=100, k=1)
    )


# --- Sprint 62: independent metric classes -- each is a thin wrapper around
# the function it shares a name with above; these are regression tests
# proving the class delegates to (never reimplements) that same function.


@pytest.mark.parametrize(
    ("metric_class", "expected_function"),
    [
        (PrecisionAtK, precision_at_k),
        (RecallAtK, recall_at_k),
        (MeanAveragePrecisionAtK, average_precision_at_k),
        (NdcgAtK, ndcg_at_k),
        (HitRateAtK, hit_rate_at_k),
    ],
)
def test_metric_class_matches_its_underlying_function(
    metric_class: type, expected_function: _RankingMetric
) -> None:
    relevant = frozenset({A, B})
    recommended = [A, X, B, Y, Z]

    metric = metric_class()

    assert metric.compute(recommended, relevant, k=5) == pytest.approx(
        expected_function(recommended, relevant, 5)
    )


@pytest.mark.parametrize(
    ("metric_class", "expected_name"),
    [
        (PrecisionAtK, "precision_at_k"),
        (RecallAtK, "recall_at_k"),
        (MeanAveragePrecisionAtK, "map_at_k"),
        (NdcgAtK, "ndcg_at_k"),
        (HitRateAtK, "hit_rate_at_k"),
    ],
)
def test_metric_class_name_matches_evaluation_result_field(
    metric_class: type, expected_name: str
) -> None:
    assert metric_class().name == expected_name


def test_standard_metrics_are_independently_iterable() -> None:
    relevant = frozenset({A})
    recommended = [A, X, Y]

    results = {
        metric.name: metric.compute(recommended, relevant, k=3) for metric in STANDARD_METRICS
    }

    assert set(results) == {
        "precision_at_k",
        "recall_at_k",
        "map_at_k",
        "ndcg_at_k",
        "hit_rate_at_k",
    }
    assert all(isinstance(value, float) for value in results.values())


def test_standard_metrics_are_deterministic_across_repeated_calls() -> None:
    relevant = frozenset({A, B})
    recommended = [B, X, A, Y, Z]

    first = [metric.compute(recommended, relevant, k=5) for metric in STANDARD_METRICS]
    second = [metric.compute(recommended, relevant, k=5) for metric in STANDARD_METRICS]

    assert first == second
