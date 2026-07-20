import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.ranking_strategies import (
    ReciprocalRankFusionStrategy,
    WeightedScoreFusionStrategy,
)
from readmatch_ai.domain.ranking_strategy import RankingCandidateList
from readmatch_ai.domain.recommendation import RecommendationItem


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def _item(book: Book, score: float, source: str) -> RecommendationItem:
    return RecommendationItem(book=book, score=score, source=source)


# --- WeightedScoreFusionStrategy ---


def test_weighted_fusion_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        WeightedScoreFusionStrategy({"popularity": -0.1})


def test_weighted_fusion_returns_empty_for_no_active_candidates() -> None:
    strategy = WeightedScoreFusionStrategy({"popularity": 1.0})

    result = strategy.fuse([RankingCandidateList("popularity", [])], limit=10)

    assert result == []


def test_weighted_fusion_merges_a_book_present_in_multiple_sources() -> None:
    shared = _book("978-3-16-148410-0", "Shared")
    popularity_only = _book("0-306-40615-2", "PopularityOnly")
    semantic_only = _book("9780132350884", "SemanticOnly")
    popularity_list = RankingCandidateList(
        "popularity",
        [_item(shared, 100.0, "popularity"), _item(popularity_only, 10.0, "popularity")],
    )
    semantic_list = RankingCandidateList(
        "semantic", [_item(shared, 0.9, "semantic"), _item(semantic_only, 0.1, "semantic")]
    )
    strategy = WeightedScoreFusionStrategy({"popularity": 0.5, "semantic": 0.5})

    result = strategy.fuse([popularity_list, semantic_list], limit=10)

    items_by_title = {item.book.title.value: item for item in result}
    assert items_by_title["Shared"].score == pytest.approx(1.0)
    assert items_by_title["Shared"].score > items_by_title["PopularityOnly"].score
    assert items_by_title["Shared"].score > items_by_title["SemanticOnly"].score
    assert all(item.source == "hybrid" for item in result)


def test_weighted_fusion_renormalizes_weights_to_active_sources_only() -> None:
    """A source contributing no candidates (e.g. no book_id/user_id this
    call) must not silently scale down the combined score of the sources
    that did contribute -- generalizes the old Popularity-only cold-start
    fallback to any number/combination of sources.
    """
    book = _book("978-3-16-148410-0")
    popularity_list = RankingCandidateList("popularity", [_item(book, 10.0, "popularity")])
    empty_semantic_list = RankingCandidateList("semantic", [])
    strategy = WeightedScoreFusionStrategy({"popularity": 0.3, "semantic": 0.7})

    result = strategy.fuse([popularity_list, empty_semantic_list], limit=10)

    assert len(result) == 1
    assert result[0].score == pytest.approx(1.0)


def test_weighted_fusion_splits_evenly_when_no_active_source_has_a_configured_weight() -> None:
    book = _book("978-3-16-148410-0")
    popularity_list = RankingCandidateList("popularity", [_item(book, 10.0, "popularity")])
    strategy = WeightedScoreFusionStrategy({})

    result = strategy.fuse([popularity_list], limit=10)

    assert result[0].score == pytest.approx(1.0)


def test_weighted_fusion_respects_limit() -> None:
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]]
    candidate_list = RankingCandidateList(
        "popularity", [_item(book, float(10 - i), "popularity") for i, book in enumerate(books)]
    )
    strategy = WeightedScoreFusionStrategy({"popularity": 1.0})

    result = strategy.fuse([candidate_list], limit=2)

    assert len(result) == 2


def test_weighted_fusion_breaks_ties_deterministically_by_book_id() -> None:
    a = _book("978-3-16-148410-0", "A")
    b = _book("0-306-40615-2", "B")
    candidate_list = RankingCandidateList(
        "popularity", [_item(a, 10.0, "popularity"), _item(b, 10.0, "popularity")]
    )
    strategy = WeightedScoreFusionStrategy({"popularity": 1.0})

    result = strategy.fuse([candidate_list], limit=10)

    expected_order = sorted([a, b], key=lambda book: str(book.id.value))
    assert [item.book for item in result] == expected_order


# --- ReciprocalRankFusionStrategy ---


def test_rrf_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        ReciprocalRankFusionStrategy(k=0)


def test_rrf_returns_empty_for_no_candidates() -> None:
    strategy = ReciprocalRankFusionStrategy()

    assert strategy.fuse([], limit=10) == []


def test_rrf_scores_a_single_source_by_rank_position() -> None:
    first = _book("978-3-16-148410-0", "First")
    second = _book("0-306-40615-2", "Second")
    candidate_list = RankingCandidateList(
        "popularity", [_item(first, 100.0, "popularity"), _item(second, 1.0, "popularity")]
    )
    strategy = ReciprocalRankFusionStrategy(k=60)

    result = strategy.fuse([candidate_list], limit=10)

    assert result[0].book == first
    assert result[0].score == pytest.approx(1 / 61)
    assert result[1].book == second
    assert result[1].score == pytest.approx(1 / 62)


def test_rrf_ignores_raw_scores_and_uses_only_rank() -> None:
    book = _book("978-3-16-148410-0")
    huge_score_list = RankingCandidateList("popularity", [_item(book, 1_000_000.0, "popularity")])
    tiny_score_list = RankingCandidateList("semantic", [_item(book, 0.0001, "semantic")])
    strategy = ReciprocalRankFusionStrategy(k=60)

    result_huge = strategy.fuse([huge_score_list], limit=10)
    result_tiny = strategy.fuse([tiny_score_list], limit=10)

    assert result_huge[0].score == pytest.approx(result_tiny[0].score)


def test_rrf_merges_duplicates_by_summing_reciprocal_ranks() -> None:
    book = _book("978-3-16-148410-0")
    popularity_list = RankingCandidateList("popularity", [_item(book, 1.0, "popularity")])
    semantic_list = RankingCandidateList("semantic", [_item(book, 1.0, "semantic")])
    strategy = ReciprocalRankFusionStrategy(k=60)

    result = strategy.fuse([popularity_list, semantic_list], limit=10)

    assert len(result) == 1
    assert result[0].score == pytest.approx(2 / 61)
    assert result[0].source == "hybrid"


def test_rrf_respects_limit() -> None:
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]]
    candidate_list = RankingCandidateList(
        "popularity", [_item(book, 1.0, "popularity") for book in books]
    )
    strategy = ReciprocalRankFusionStrategy()

    result = strategy.fuse([candidate_list], limit=2)

    assert len(result) == 2


def test_rrf_breaks_ties_deterministically_by_book_id() -> None:
    a = _book("978-3-16-148410-0", "A")
    b = _book("0-306-40615-2", "B")
    list1 = RankingCandidateList("popularity", [_item(a, 1.0, "popularity")])
    list2 = RankingCandidateList("semantic", [_item(b, 1.0, "semantic")])
    strategy = ReciprocalRankFusionStrategy()

    result = strategy.fuse([list1, list2], limit=10)

    expected_order = sorted([a, b], key=lambda book: str(book.id.value))
    assert [item.book for item in result] == expected_order
