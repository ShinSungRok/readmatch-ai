from __future__ import annotations

from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.application.generate_hybrid_recommendation_use_case import (
    GenerateHybridRecommendationUseCase,
)
from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.home_feed import HomeFeed, HomeFeedItem, HomeFeedSection
from readmatch_ai.domain.recommendation import RecommendationItem

_MINIMUM_BOOKS_PER_CATEGORY = 2


class GetHomeFeedUseCase:
    """Composes existing recommendation use cases into one consolidated home-feed response.

    Reimplements no ranking or scoring: every section's items, scores, and
    sources come straight from the same GetRecommendationsUseCase/
    GenerateHybridRecommendationUseCase/GenerateSemanticRecommendationUseCase
    instances the individual recommendation endpoints already use (injected,
    not rebuilt here, so a real call through either path is metered/logged
    exactly once by ApplicationContext's existing observability wiring).
    This only decides *which* of their results to group into which section,
    and enriches each book with presentation data via the existing
    GetBookPresentationUseCase (Sprint 39) -- a presentation/UI concern,
    kept separate from the recommendation results themselves.
    """

    def __init__(
        self,
        popularity_use_case: GetRecommendationsUseCase,
        hybrid_use_case: GenerateHybridRecommendationUseCase,
        semantic_use_case: GenerateSemanticRecommendationUseCase,
        book_presentation_use_case: GetBookPresentationUseCase,
    ) -> None:
        self._popularity_use_case = popularity_use_case
        self._hybrid_use_case = hybrid_use_case
        self._semantic_use_case = semantic_use_case
        self._book_presentation_use_case = book_presentation_use_case

    def execute(self, limit: int = 12) -> HomeFeed:
        """Build the home feed for the given per-section item limit.

        Deterministic for the same inputs: every underlying use case is
        already deterministic, and this method introduces no randomness of
        its own (grouping/sorting only, never a re-ranking pass). If there
        are no books at all, returns an empty feed (`hero=None`,
        `sections=[]`) rather than an error -- the same safe default
        every recommendation endpoint already returns for an empty result.
        """
        popularity_items = self._popularity_use_case.execute(limit=limit).recommendation.items
        if not popularity_items:
            return HomeFeed(hero=None, sections=[])

        hero_item = popularity_items[0]
        hero_book_id = str(hero_item.book.id.value)

        hybrid_items = self._hybrid_use_case.execute(limit=limit).recommendation.items
        semantic_items = self._semantic_use_case.execute(
            book_id=hero_book_id, limit=limit
        ).recommendation.items

        # One batch presentation lookup for every book this feed will ever
        # reference (hero + every section, including category groupings,
        # which only regroup these same three item lists) -- one
        # BookMetadataRepository round-trip total, not one per item.
        all_items = popularity_items + hybrid_items + semantic_items
        presentations = self._book_presentation_use_case.execute_many(
            [item.book for item in all_items]
        )

        sections = [
            HomeFeedSection(
                id="popular",
                title="Popular books",
                items=self._to_home_feed_items(popularity_items, presentations),
            ),
            HomeFeedSection(
                id="recommended",
                title="Recommended picks",
                items=self._to_home_feed_items(hybrid_items, presentations),
            ),
        ]
        if semantic_items:
            # Omitted entirely (not an empty section) when the hero book has
            # no embedding yet -- the same "unavailable section" handling as
            # GET /recommendations/semantic/{book_id} itself.
            sections.append(
                HomeFeedSection(
                    id="similar-to-hero",
                    title=f"Similar to {hero_item.book.title.value}",
                    items=self._to_home_feed_items(semantic_items, presentations),
                )
            )
        sections.extend(
            self._build_category_sections(
                [popularity_items, hybrid_items, semantic_items], presentations
            )
        )

        hero = HomeFeedItem(
            book=presentations[hero_book_id],
            score=hero_item.score,
            source=hero_item.source,
        )
        return HomeFeed(hero=hero, sections=sections)

    @staticmethod
    def _to_home_feed_items(
        items: list[RecommendationItem], presentations: dict[str, BookPresentation]
    ) -> list[HomeFeedItem]:
        return [
            HomeFeedItem(
                book=presentations[str(item.book.id.value)], score=item.score, source=item.source
            )
            for item in items
        ]

    def _build_category_sections(
        self,
        item_lists: list[list[RecommendationItem]],
        presentations: dict[str, BookPresentation],
    ) -> list[HomeFeedSection]:
        """Group already-ranked items by category for display.

        Pure presentation shaping, not a new ranking algorithm: each book id
        is kept once (first occurrence across `item_lists` wins), categories
        with fewer than `_MINIMUM_BOOKS_PER_CATEGORY` books are dropped, and
        the result is sorted by category name for a deterministic order.
        """
        seen_book_ids: set[str] = set()
        items_by_category: dict[str, list[RecommendationItem]] = {}
        for items in item_lists:
            for item in items:
                book_id = str(item.book.id.value)
                if book_id in seen_book_ids:
                    continue
                seen_book_ids.add(book_id)
                items_by_category.setdefault(item.book.category.value, []).append(item)

        return [
            HomeFeedSection(
                id=f"category-{_slugify(category)}",
                title=f"More in {category}",
                items=self._to_home_feed_items(items, presentations),
            )
            for category, items in sorted(items_by_category.items())
            if len(items) >= _MINIMUM_BOOKS_PER_CATEGORY
        ]


def _slugify(category: str) -> str:
    return "-".join(category.lower().split())
