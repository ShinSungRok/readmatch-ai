from collections.abc import Callable

import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import RecommendationItem
from readmatch_ai.domain.reranker import (
    DefaultRecommendationReranker,
    RecommendationReranker,
    RerankingContext,
    RerankingPolicy,
)
from readmatch_ai.domain.user import UserId


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def _item(book: Book, score: float) -> RecommendationItem:
    return RecommendationItem(book=book, score=score, source="fake")


def test_reranking_policy_is_abstract() -> None:
    with pytest.raises(TypeError):
        RerankingPolicy()  # type: ignore[abstract]


def test_recommendation_reranker_is_abstract() -> None:
    with pytest.raises(TypeError):
        RecommendationReranker()  # type: ignore[abstract]


class _RecordingPolicy(RerankingPolicy):
    """Records the arguments it was called with and returns a fixed transformation."""

    def __init__(
        self, transform: Callable[[list[RecommendationItem]], list[RecommendationItem]]
    ) -> None:
        self._transform = transform
        self.received_items: list[RecommendationItem] | None = None
        self.received_limit: int | None = None
        self.received_context: RerankingContext | None = None

    def apply(
        self, items: list[RecommendationItem], limit: int, context: RerankingContext
    ) -> list[RecommendationItem]:
        self.received_items = items
        self.received_limit = limit
        self.received_context = context
        return self._transform(items)


def test_default_reranker_chains_policies_in_order() -> None:
    book_a, book_b = _book("978-3-16-148410-0", "A"), _book("0-306-40615-2", "B")
    items = [_item(book_a, 1.0), _item(book_b, 2.0)]
    reverse_policy = _RecordingPolicy(lambda items: list(reversed(items)))
    identity_policy = _RecordingPolicy(lambda items: items)
    reranker = DefaultRecommendationReranker([reverse_policy, identity_policy])

    result = reranker.rerank(items, limit=2, context=RerankingContext())

    assert reverse_policy.received_items == items
    assert identity_policy.received_items == list(reversed(items))
    assert result == list(reversed(items))


def test_default_reranker_passes_limit_and_context_to_each_policy() -> None:
    context = RerankingContext(user_id=UserId.generate())
    policy = _RecordingPolicy(lambda items: items)
    reranker = DefaultRecommendationReranker([policy])

    reranker.rerank([], limit=5, context=context)

    assert policy.received_limit == 5
    assert policy.received_context == context


def test_default_reranker_truncates_to_limit_even_if_a_policy_does_not() -> None:
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]]
    items = [_item(book, float(i)) for i, book in enumerate(books)]
    passthrough_policy = _RecordingPolicy(lambda items: items)
    reranker = DefaultRecommendationReranker([passthrough_policy])

    result = reranker.rerank(items, limit=2, context=RerankingContext())

    assert len(result) == 2


def test_default_reranker_with_no_policies_only_truncates() -> None:
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2"]]
    items = [_item(book, float(i)) for i, book in enumerate(books)]
    reranker = DefaultRecommendationReranker([])

    result = reranker.rerank(items, limit=1, context=RerankingContext())

    assert result == items[:1]
