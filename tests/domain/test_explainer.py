import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.explainer import (
    COLLABORATIVE_BEHAVIOR_REASON,
    DIVERSITY_REASON,
    NOVELTY_REASON,
    POPULARITY_REASON,
    SEMANTIC_SIMILARITY_REASON,
    DefaultRecommendationExplainer,
    ExplanationContext,
    RecommendationExplainer,
)
from readmatch_ai.domain.recommendation import (
    ALS_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    RecommendationItem,
)
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
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


def _item(
    book: Book, score: float = 1.0, contributing_sources: frozenset[str] = frozenset()
) -> RecommendationItem:
    return RecommendationItem(
        book=book, score=score, source="hybrid", contributing_sources=contributing_sources
    )


def test_recommendation_explainer_is_abstract() -> None:
    with pytest.raises(TypeError):
        RecommendationExplainer()  # type: ignore[abstract]


def test_explain_returns_one_explanation_per_item_in_order() -> None:
    a, b = _book("978-3-16-148410-0", title="A"), _book("0-306-40615-2", title="B")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain([_item(a), _item(b)], ExplanationContext())

    assert [explanation.book_id for explanation in explanations] == [a.id, b.id]


def test_popularity_reason_requires_popularity_in_contributing_sources() -> None:
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    with_evidence = explainer.explain(
        [_item(book, contributing_sources=frozenset({POPULARITY_SOURCE}))], ExplanationContext()
    )
    without_evidence = explainer.explain([_item(book)], ExplanationContext())

    assert [r.type for r in with_evidence[0].reasons] == [POPULARITY_REASON]
    assert without_evidence[0].reasons == ()


def test_semantic_reason_requires_semantic_in_contributing_sources() -> None:
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())
    context = ExplanationContext(book_id=BookId.generate())

    with_evidence = explainer.explain(
        [_item(book, contributing_sources=frozenset({SEMANTIC_SOURCE}))], context
    )
    without_evidence = explainer.explain([_item(book)], context)

    assert [r.type for r in with_evidence[0].reasons] == [SEMANTIC_SIMILARITY_REASON]
    assert without_evidence[0].reasons == ()


def test_semantic_reason_absent_without_book_id_even_if_contributing_sources_claims_it() -> None:
    """Structurally, semantic can never contribute without a book_id query --
    SemanticRecommendationEngine itself requires one -- but this confirms
    the explainer doesn't fabricate the reason if that invariant were ever
    violated upstream: contributing_sources is the sole evidence used.
    """
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain(
        [_item(book, contributing_sources=frozenset({SEMANTIC_SOURCE}))],
        ExplanationContext(book_id=None),
    )

    # Evidence-only gating: contributing_sources alone is sufficient/necessary.
    assert [r.type for r in explanations[0].reasons] == [SEMANTIC_SIMILARITY_REASON]


def test_collaborative_reason_requires_als_in_contributing_sources() -> None:
    book = _book("978-3-16-148410-0")
    user_id = UserId.generate()
    # Record an interaction with this exact book so novelty doesn't also
    # fire, isolating the collaborative-behavior reason's own evidence.
    interactions = InMemoryUserBookInteractionRepository()
    interactions.record(UserBookInteraction(user_id, book.id, interaction_count=1))
    explainer = DefaultRecommendationExplainer(interactions)
    context = ExplanationContext(user_id=user_id)

    with_evidence = explainer.explain(
        [_item(book, contributing_sources=frozenset({ALS_SOURCE}))], context
    )
    without_evidence = explainer.explain([_item(book)], context)

    assert [r.type for r in with_evidence[0].reasons] == [COLLABORATIVE_BEHAVIOR_REASON]
    assert without_evidence[0].reasons == ()


def test_novelty_reason_fires_when_user_has_not_interacted_with_the_book() -> None:
    book = _book("978-3-16-148410-0")
    user_id = UserId.generate()
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain([_item(book)], ExplanationContext(user_id=user_id))

    assert [r.type for r in explanations[0].reasons] == [NOVELTY_REASON]


def test_novelty_reason_absent_when_user_has_interacted_with_the_book() -> None:
    book = _book("978-3-16-148410-0")
    user_id = UserId.generate()
    interactions = InMemoryUserBookInteractionRepository()
    interactions.record(UserBookInteraction(user_id, book.id, interaction_count=1))
    explainer = DefaultRecommendationExplainer(interactions)

    explanations = explainer.explain([_item(book)], ExplanationContext(user_id=user_id))

    assert explanations[0].reasons == ()


def test_novelty_reason_absent_without_a_user_id() -> None:
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain([_item(book)], ExplanationContext())

    assert explanations[0].reasons == ()


def test_cold_start_user_with_no_interactions_gets_novelty_but_not_collaborative() -> None:
    """An unknown/new user has an empty interaction history: every book is
    truthfully "not yet interacted with" (novelty), but nothing can claim
    collaborative-filtering evidence since ALS never contributed either.
    """
    book = _book("978-3-16-148410-0")
    user_id = UserId.generate()
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain([_item(book)], ExplanationContext(user_id=user_id))

    assert [r.type for r in explanations[0].reasons] == [NOVELTY_REASON]


def test_diversity_reason_fires_for_the_first_item_of_a_new_category_but_not_the_first_item() -> (
    None
):
    first = _book("978-3-16-148410-0", category="Fiction")
    same_category_second = _book("0-306-40615-2", category="Fiction")
    new_category_third = _book("9780132350884", category="History")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain(
        [_item(first), _item(same_category_second), _item(new_category_third)],
        ExplanationContext(),
    )

    assert DIVERSITY_REASON not in [r.type for r in explanations[0].reasons]
    assert DIVERSITY_REASON not in [r.type for r in explanations[1].reasons]
    assert [r.type for r in explanations[2].reasons] == [DIVERSITY_REASON]


def test_reasons_are_returned_in_canonical_deterministic_order() -> None:
    book = _book("978-3-16-148410-0", category="Fiction")
    other_category_book = _book("0-306-40615-2", category="History")
    user_id = UserId.generate()
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())
    context = ExplanationContext(book_id=BookId.generate(), user_id=user_id)
    items = [
        _item(book, contributing_sources=frozenset({ALS_SOURCE, SEMANTIC_SOURCE})),
        _item(
            other_category_book,
            contributing_sources=frozenset({POPULARITY_SOURCE, SEMANTIC_SOURCE, ALS_SOURCE}),
        ),
    ]

    explanations = explainer.explain(items, context)

    assert [r.type for r in explanations[0].reasons] == [
        SEMANTIC_SIMILARITY_REASON,
        COLLABORATIVE_BEHAVIOR_REASON,
        NOVELTY_REASON,
    ]
    assert [r.type for r in explanations[1].reasons] == [
        POPULARITY_REASON,
        SEMANTIC_SIMILARITY_REASON,
        COLLABORATIVE_BEHAVIOR_REASON,
        NOVELTY_REASON,
        DIVERSITY_REASON,
    ]


def test_explain_is_deterministic_across_repeated_calls() -> None:
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())
    context = ExplanationContext(user_id=UserId.generate())
    item = _item(book, contributing_sources=frozenset({POPULARITY_SOURCE}))

    first_call = explainer.explain([item], context)
    second_call = explainer.explain([item], context)

    assert first_call == second_call


def test_reasons_carry_no_fabricated_confidence_value() -> None:
    book = _book("978-3-16-148410-0")
    explainer = DefaultRecommendationExplainer(InMemoryUserBookInteractionRepository())

    explanations = explainer.explain(
        [_item(book, contributing_sources=frozenset({POPULARITY_SOURCE}))], ExplanationContext()
    )

    reason = explanations[0].reasons[0]
    assert not hasattr(reason, "confidence")
    assert set(vars(reason)) == {"type", "message"}
