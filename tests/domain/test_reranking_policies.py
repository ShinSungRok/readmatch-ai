import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.recommendation import RecommendationItem
from readmatch_ai.domain.reranker import RerankingContext
from readmatch_ai.domain.reranking_policies import (
    ExplicitFeedbackPolicy,
    MMRDiversityPolicy,
    NoveltyBoostPolicy,
    PopularityPenaltyPolicy,
)
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)


def _book(isbn: str, category: str = "Category", title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category(category),
    )


def _item(book: Book, score: float) -> RecommendationItem:
    return RecommendationItem(book=book, score=score, source="fake")


# --- MMRDiversityPolicy ---


def test_mmr_rejects_lambda_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="lambda_param"):
        MMRDiversityPolicy(lambda_param=1.5)


def test_mmr_returns_empty_for_empty_items() -> None:
    policy = MMRDiversityPolicy()

    assert policy.apply([], limit=5, context=RerankingContext()) == []


def test_mmr_with_lambda_one_behaves_like_a_plain_relevance_sort() -> None:
    a = _book("978-3-16-148410-0", "Software Engineering", "A")
    b = _book("0-306-40615-2", "Software Engineering", "B")
    c = _book("9780132350884", "Science Fiction", "C")
    items = [_item(a, 10.0), _item(b, 5.0), _item(c, 1.0)]
    policy = MMRDiversityPolicy(lambda_param=1.0)

    result = policy.apply(items, limit=3, context=RerankingContext())

    assert [item.book for item in result] == [a, b, c]


def test_mmr_diversifies_a_lower_scoring_different_category_item_over_a_similar_one() -> None:
    """a and b share a category (high relevance); c is a different category
    but much lower relevance -- a diversity-weighted MMR should still
    surface c ahead of b, since b is redundant with the already-selected a.
    """
    a = _book("978-3-16-148410-0", "Software Engineering", "A")
    b = _book("0-306-40615-2", "Software Engineering", "B")
    c = _book("9780132350884", "Science Fiction", "C")
    items = [_item(a, 10.0), _item(b, 9.0), _item(c, 1.0)]
    policy = MMRDiversityPolicy(lambda_param=0.3)

    result = policy.apply(items, limit=2, context=RerankingContext())

    assert [item.book for item in result] == [a, c]


def test_mmr_respects_limit() -> None:
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]]
    items = [_item(book, float(i)) for i, book in enumerate(books)]
    policy = MMRDiversityPolicy()

    result = policy.apply(items, limit=2, context=RerankingContext())

    assert len(result) == 2


def test_mmr_breaks_ties_deterministically_by_book_id() -> None:
    a = _book("978-3-16-148410-0", "Category", "A")
    b = _book("0-306-40615-2", "Category", "B")
    items = [_item(a, 1.0), _item(b, 1.0)]
    policy = MMRDiversityPolicy()

    result = policy.apply(items, limit=2, context=RerankingContext())

    expected_order = sorted([a, b], key=lambda book: str(book.id.value))
    assert [item.book for item in result] == expected_order


# --- ExplicitFeedbackPolicy ---


def test_explicit_feedback_rejects_negative_boost() -> None:
    with pytest.raises(ValueError, match="boost"):
        ExplicitFeedbackPolicy(InMemoryInteractionRepository(), boost=-0.1)


def test_explicit_feedback_is_a_noop_without_a_user_id() -> None:
    book = _book("978-3-16-148410-0")
    items = [_item(book, 1.0)]
    policy = ExplicitFeedbackPolicy(InMemoryInteractionRepository())

    result = policy.apply(items, limit=1, context=RerankingContext())

    assert result == items


def test_explicit_feedback_preserves_baseline_when_user_has_no_interactions() -> None:
    a = _book("978-3-16-148410-0")
    b = _book("0-306-40615-2")
    items = [_item(a, 2.0), _item(b, 1.0)]
    policy = ExplicitFeedbackPolicy(InMemoryInteractionRepository())

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=UserId.generate()))

    assert result == items


def test_explicit_feedback_boosts_a_liked_book() -> None:
    liked = _book("978-3-16-148410-0", title="Liked")
    other = _book("0-306-40615-2", title="Other")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, liked.id, InteractionType.LIKE))
    # Liked starts with a lower raw score than Other.
    items = [_item(other, 1.0), _item(liked, 0.9)]
    policy = ExplicitFeedbackPolicy(interactions, boost=0.5)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [liked, other]


def test_explicit_feedback_boosts_a_bookmarked_book() -> None:
    bookmarked = _book("978-3-16-148410-0", title="Bookmarked")
    other = _book("0-306-40615-2", title="Other")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, bookmarked.id, InteractionType.BOOKMARK))
    items = [_item(other, 1.0), _item(bookmarked, 0.9)]
    policy = ExplicitFeedbackPolicy(interactions, boost=0.5)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [bookmarked, other]


def test_explicit_feedback_boosts_a_highly_rated_book() -> None:
    rated = _book("978-3-16-148410-0", title="Rated")
    other = _book("0-306-40615-2", title="Other")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, rated.id, InteractionType.RATING, value=5))
    items = [_item(other, 1.0), _item(rated, 0.9)]
    policy = ExplicitFeedbackPolicy(interactions, boost=0.5)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [rated, other]


def test_explicit_feedback_excludes_a_disliked_book() -> None:
    disliked = _book("978-3-16-148410-0")
    other = _book("0-306-40615-2")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, disliked.id, InteractionType.DISLIKE))
    items = [_item(disliked, 5.0), _item(other, 1.0)]
    policy = ExplicitFeedbackPolicy(interactions)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [other]


def test_explicit_feedback_excludes_a_read_book() -> None:
    read = _book("978-3-16-148410-0")
    other = _book("0-306-40615-2")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, read.id, InteractionType.READ))
    items = [_item(read, 5.0), _item(other, 1.0)]
    policy = ExplicitFeedbackPolicy(interactions)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [other]


def test_explicit_feedback_excludes_a_poorly_rated_book() -> None:
    rated = _book("978-3-16-148410-0")
    other = _book("0-306-40615-2")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, rated.id, InteractionType.RATING, value=1))
    items = [_item(rated, 5.0), _item(other, 1.0)]
    policy = ExplicitFeedbackPolicy(interactions)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [other]


def test_explicit_feedback_neutral_rating_neither_boosts_nor_excludes() -> None:
    rated = _book("978-3-16-148410-0")
    other = _book("0-306-40615-2")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, rated.id, InteractionType.RATING, value=3))
    items = [_item(other, 2.0), _item(rated, 1.0)]
    policy = ExplicitFeedbackPolicy(interactions, boost=0.5)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [other, rated]


def test_explicit_feedback_click_interactions_have_no_effect() -> None:
    clicked = _book("978-3-16-148410-0")
    other = _book("0-306-40615-2")
    user_id = UserId.generate()
    interactions = InMemoryInteractionRepository()
    interactions.record(UserInteraction(user_id, clicked.id, InteractionType.CLICK))
    items = [_item(clicked, 2.0), _item(other, 1.0)]
    policy = ExplicitFeedbackPolicy(interactions, boost=0.5)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [clicked, other]


# --- NoveltyBoostPolicy ---


def test_novelty_boost_rejects_negative_boost() -> None:
    with pytest.raises(ValueError, match="boost"):
        NoveltyBoostPolicy(InMemoryUserBookInteractionRepository(), boost=-0.1)


def test_novelty_boost_is_a_noop_without_a_user_id() -> None:
    book = _book("978-3-16-148410-0")
    items = [_item(book, 1.0)]
    policy = NoveltyBoostPolicy(InMemoryUserBookInteractionRepository())

    result = policy.apply(items, limit=1, context=RerankingContext())

    assert result == items


def test_novelty_boost_promotes_unknown_books_over_known_ones() -> None:
    known = _book("978-3-16-148410-0", title="Known")
    unknown = _book("0-306-40615-2", title="Unknown")
    user_id = UserId.generate()
    interactions = InMemoryUserBookInteractionRepository()
    interactions.record(UserBookInteraction(user_id=user_id, book_id=known.id, interaction_count=1))
    # Known starts with a higher raw score than Unknown.
    items = [_item(known, 10.0), _item(unknown, 9.0)]
    policy = NoveltyBoostPolicy(interactions, boost=5.0)

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=user_id))

    assert [item.book for item in result] == [unknown, known]


def test_novelty_boost_does_not_change_order_when_no_books_are_known() -> None:
    a = _book("978-3-16-148410-0")
    b = _book("0-306-40615-2")
    items = [_item(a, 2.0), _item(b, 1.0)]
    policy = NoveltyBoostPolicy(InMemoryUserBookInteractionRepository())

    result = policy.apply(items, limit=2, context=RerankingContext(user_id=UserId.generate()))

    assert [item.book for item in result] == [a, b]


# --- PopularityPenaltyPolicy ---


def test_popularity_penalty_rejects_penalty_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="penalty"):
        PopularityPenaltyPolicy(InMemoryBookPopularityRepository(), penalty=1.5)


def test_popularity_penalty_returns_empty_for_empty_items() -> None:
    policy = PopularityPenaltyPolicy(InMemoryBookPopularityRepository())

    assert policy.apply([], limit=5, context=RerankingContext()) == []


def test_popularity_penalty_demotes_a_highly_popular_item() -> None:
    popular = _book("978-3-16-148410-0", title="Popular")
    niche = _book("0-306-40615-2", title="Niche")
    repository = InMemoryBookPopularityRepository()
    repository.record(BookPopularity(popular.id, 1000, "2024-01-01", "2024-01-31"))
    repository.record(BookPopularity(niche.id, 10, "2024-01-01", "2024-01-31"))
    # Equal starting scores, so the penalty alone must decide the order.
    items = [_item(popular, 1.0), _item(niche, 1.0)]
    policy = PopularityPenaltyPolicy(repository, penalty=0.9)

    result = policy.apply(items, limit=2, context=RerankingContext())

    assert [item.book for item in result] == [niche, popular]


def test_popularity_penalty_treats_unrecorded_popularity_as_zero() -> None:
    book = _book("978-3-16-148410-0")
    items = [_item(book, 1.0)]
    policy = PopularityPenaltyPolicy(InMemoryBookPopularityRepository(), penalty=0.5)

    result = policy.apply(items, limit=1, context=RerankingContext())

    assert result[0].score == pytest.approx(1.0)


def test_popularity_penalty_breaks_ties_deterministically_by_book_id() -> None:
    a = _book("978-3-16-148410-0")
    b = _book("0-306-40615-2")
    items = [_item(a, 1.0), _item(b, 1.0)]
    policy = PopularityPenaltyPolicy(InMemoryBookPopularityRepository())

    result = policy.apply(items, limit=2, context=RerankingContext())

    expected_order = sorted([a, b], key=lambda book: str(book.id.value))
    assert [item.book for item in result] == expected_order
