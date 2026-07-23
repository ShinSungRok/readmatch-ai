from __future__ import annotations

import uuid

from readmatch_ai.application.explained_personalized_recommendation import (
    ExplainedPersonalizedRecommendationItem,
    ExplainedPersonalizedRecommendationResult,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_user_preference_profile_use_case import (
    GetUserPreferenceProfileUseCase,
)
from readmatch_ai.application.user_preference_profile import UserPreferenceProfile
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.explainer import (
    ExplanationContext,
    ExplanationReason,
    RecommendationExplainer,
    RecommendationExplanation,
)
from readmatch_ai.domain.recommendation import RecommendationItem, RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId

FAVORITE_CATEGORY_REASON = "favorite_category"
FAVORITE_AUTHOR_REASON = "favorite_author"
RECENT_SEARCH_MATCH_REASON = "recent_search_match"


class GenerateExplainedPersonalizedRecommendationUseCase:
    """Generates personalized recommendations, then explains the already-produced result.

    Mirrors GenerateRerankedRecommendationUseCase's query-building exactly
    (the injected RecommendationEngine is expected to be the same
    RerankedRecommendationEngine wrapping Hybrid ranking), so the ranked
    items are identical to what the non-explained personalized endpoint
    would return -- no second, independent ranking pass. The injected
    RecommendationExplainer only inspects that already-produced result.

    Sprint 14 additionally appends reasons derived from the user's own
    UserPreferenceProfile (favorite_category/favorite_author/
    recent_search_match) -- evidence the Domain explainer itself has no
    access to (it only sees RecommendationItems and the implicit
    UserBookInteractionRepository). This still never runs a second ranking
    pass: the profile only annotates the same already-produced, already-
    ordered items with additional truthful text, in the Application layer
    (never in domain.explainer -- that stays untouched).

    Also enriches every item via the existing GetBookPresentationUseCase
    (one execute_many() batch call, not one lookup per item) and returns
    ExplainedPersonalizedRecommendationResult (book: BookPresentation)
    instead of the Domain's own ExplainedRecommendationResult (book: Book)
    -- so GET /recommendations/personalized/{user_id}/explained returns
    the same book payload shape (cover_url/publisher/description/
    published_date included) the Home Feed already does, without adding
    any metadata to RecommendationItem or the Domain explainer itself.
    """

    def __init__(
        self,
        recommendation_engine: RecommendationEngine,
        explainer: RecommendationExplainer,
        preference_profile_use_case: GetUserPreferenceProfileUseCase,
        book_presentation_use_case: GetBookPresentationUseCase,
    ) -> None:
        self._recommendation_engine = recommendation_engine
        self._explainer = explainer
        self._preference_profile_use_case = preference_profile_use_case
        self._book_presentation_use_case = book_presentation_use_case

    def execute(
        self, limit: int, book_id: str | None = None, user_id: str | None = None
    ) -> ExplainedPersonalizedRecommendationResult:
        query_book_id = BookId(uuid.UUID(book_id)) if book_id is not None else None
        query_user_id = UserId(uuid.UUID(user_id)) if user_id is not None else None
        query = RecommendationQuery(limit=limit, book_id=query_book_id, user_id=query_user_id)

        items = self._recommendation_engine.recommend(query).recommendation.items
        context = ExplanationContext(book_id=query_book_id, user_id=query_user_id)
        explanations = self._explainer.explain(items, context)
        profile = (
            self._preference_profile_use_case.execute(user_id) if user_id is not None else None
        )
        # One batch presentation lookup for every item, not one
        # BookMetadataRepository round-trip per item.
        presentations = self._book_presentation_use_case.execute_many(
            [item.book for item in items]
        )

        explained_items = [
            ExplainedPersonalizedRecommendationItem(
                book=presentations[str(item.book.id.value)],
                score=item.score,
                source=item.source,
                reasons=(
                    explanation
                    if profile is None
                    else _with_profile_reasons(item, explanation, profile)
                ).reasons,
            )
            for item, explanation in zip(items, explanations, strict=True)
        ]
        return ExplainedPersonalizedRecommendationResult(items=explained_items)


def _with_profile_reasons(
    item: RecommendationItem,
    explanation: RecommendationExplanation,
    profile: UserPreferenceProfile,
) -> RecommendationExplanation:
    """Appends zero or more UserPreferenceProfile-derived reasons to an existing explanation.

    Each reason states an observable match between this book and the
    user's own profile -- never a fabricated one: a category/author only
    ever appears in `profile.favorite_categories`/`favorite_authors` when
    it was actually derived from the user's own positive interactions
    (see GetUserPreferenceProfileUseCase), and a search-term match only
    fires when the term is actually a substring of this book's own title
    or category.
    """
    extra_reasons: list[ExplanationReason] = []
    category = item.book.category.value
    author = item.book.author.value

    if category in profile.favorite_categories:
        extra_reasons.append(
            ExplanationReason(
                type=FAVORITE_CATEGORY_REASON,
                message=f"You've recently engaged with several {category} books.",
            )
        )
    if author in profile.favorite_authors:
        extra_reasons.append(
            ExplanationReason(
                type=FAVORITE_AUTHOR_REASON,
                message=f"By {author}, one of your favorite authors.",
            )
        )
    matched_term = _first_matching_search_term(item, profile.recent_search_terms)
    if matched_term is not None:
        extra_reasons.append(
            ExplanationReason(
                type=RECENT_SEARCH_MATCH_REASON,
                message=f"Related to your recent search for '{matched_term}'.",
            )
        )

    if not extra_reasons:
        return explanation
    return RecommendationExplanation(
        book_id=explanation.book_id, reasons=explanation.reasons + tuple(extra_reasons)
    )


def _first_matching_search_term(
    item: RecommendationItem, recent_search_terms: tuple[str, ...]
) -> str | None:
    haystack = f"{item.book.title.value} {item.book.category.value}".casefold()
    for term in recent_search_terms:
        if term.casefold() in haystack:
            return term
    return None
