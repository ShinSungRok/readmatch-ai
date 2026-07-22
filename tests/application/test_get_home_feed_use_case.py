from readmatch_ai.application.generate_hybrid_recommendation_use_case import (
    GenerateHybridRecommendationUseCase,
)
from readmatch_ai.application.generate_semantic_recommendation_use_case import (
    GenerateSemanticRecommendationUseCase,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_home_feed_use_case import GetHomeFeedUseCase
from readmatch_ai.application.get_recommendations_use_case import GetRecommendationsUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.recommendation import (
    HYBRID_SOURCE,
    POPULARITY_SOURCE,
    SEMANTIC_SOURCE,
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class _StubEngine(RecommendationEngine):
    """Returns a fixed set of items regardless of the query -- isolates
    GetHomeFeedUseCase's own composition/grouping logic from any real
    ranking algorithm.
    """

    def __init__(self, items: list[RecommendationItem]) -> None:
        self._items = items
        self.last_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.last_query = query
        return RecommendationResult(recommendation=Recommendation(items=self._items))


def _setup() -> tuple[GetHomeFeedUseCase, _StubEngine, Book, Book, Book]:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    hero_book = register.execute(
        RegisterBookInput("978-3-16-148410-0", "Hero", "Author", "History")
    )
    other_book = register.execute(
        RegisterBookInput("0-306-40615-2", "Other", "Author", "History")
    )
    extra_book = register.execute(RegisterBookInput("9780132350884", "Extra", "Author", "Fiction"))

    hero_item = RecommendationItem(book=hero_book, score=100.0, source=POPULARITY_SOURCE)
    other_popularity_item = RecommendationItem(
        book=other_book, score=50.0, source=POPULARITY_SOURCE
    )
    other_hybrid_item = RecommendationItem(book=other_book, score=0.8, source=HYBRID_SOURCE)
    extra_semantic_item = RecommendationItem(book=extra_book, score=0.5, source=SEMANTIC_SOURCE)

    popularity_use_case = GetRecommendationsUseCase(
        _StubEngine([hero_item, other_popularity_item])
    )
    hybrid_use_case = GenerateHybridRecommendationUseCase(_StubEngine([other_hybrid_item]))
    semantic_engine = _StubEngine([extra_semantic_item])
    semantic_use_case = GenerateSemanticRecommendationUseCase(semantic_engine)
    book_presentation_use_case = GetBookPresentationUseCase(book_repository, metadata_repository)

    use_case = GetHomeFeedUseCase(
        popularity_use_case, hybrid_use_case, semantic_use_case, book_presentation_use_case
    )
    return use_case, semantic_engine, hero_book, other_book, extra_book


def test_execute_returns_an_empty_feed_when_there_are_no_popularity_items() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    use_case = GetHomeFeedUseCase(
        GetRecommendationsUseCase(_StubEngine([])),
        GenerateHybridRecommendationUseCase(_StubEngine([])),
        GenerateSemanticRecommendationUseCase(_StubEngine([])),
        GetBookPresentationUseCase(book_repository, metadata_repository),
    )

    feed = use_case.execute(limit=10)

    assert feed.hero is None
    assert feed.sections == []


def test_execute_builds_hero_and_sections_from_the_underlying_use_cases() -> None:
    use_case, semantic_engine, hero_book, other_book, extra_book = _setup()

    feed = use_case.execute(limit=10)

    assert feed.hero is not None
    assert feed.hero.book.id == str(hero_book.id.value)
    assert feed.hero.score == 100.0
    assert feed.hero.source == POPULARITY_SOURCE
    # The semantic use case is queried anchored on the hero book, not blind.
    assert semantic_engine.last_query is not None
    assert semantic_engine.last_query.book_id == hero_book.id

    sections_by_id = {section.id: section for section in feed.sections}
    assert sections_by_id["popular"].title == "Popular books"
    assert [item.book.id for item in sections_by_id["popular"].items] == [
        str(hero_book.id.value),
        str(other_book.id.value),
    ]
    assert sections_by_id["recommended"].title == "Recommended picks"
    assert [item.book.id for item in sections_by_id["recommended"].items] == [
        str(other_book.id.value)
    ]
    assert sections_by_id["similar-to-hero"].title == "Similar to Hero"
    assert [item.book.id for item in sections_by_id["similar-to-hero"].items] == [
        str(extra_book.id.value)
    ]


def test_execute_groups_books_sharing_a_category_and_drops_single_book_categories() -> None:
    use_case, _semantic_engine, hero_book, other_book, extra_book = _setup()

    feed = use_case.execute(limit=10)

    sections_by_id = {section.id: section for section in feed.sections}
    assert sections_by_id["category-history"].title == "More in History"
    assert {item.book.id for item in sections_by_id["category-history"].items} == {
        str(hero_book.id.value),
        str(other_book.id.value),
    }
    # "Extra" is the only book in "Fiction" -- not useful as a row.
    assert "category-fiction" not in sections_by_id


def test_execute_omits_similar_to_hero_section_when_semantic_has_no_results() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    book = register.execute(RegisterBookInput("978-3-16-148410-0", "Solo", "Author", "History"))
    hero_item = RecommendationItem(book=book, score=10.0, source=POPULARITY_SOURCE)
    use_case = GetHomeFeedUseCase(
        GetRecommendationsUseCase(_StubEngine([hero_item])),
        GenerateHybridRecommendationUseCase(_StubEngine([])),
        GenerateSemanticRecommendationUseCase(_StubEngine([])),
        GetBookPresentationUseCase(book_repository, metadata_repository),
    )

    feed = use_case.execute(limit=10)

    assert "similar-to-hero" not in {section.id for section in feed.sections}
