from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.popularity_recommendation_engine import (
    PopularityRecommendationEngine,
)


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def _engine(
    book_repository: InMemoryBookRepository, popularity_repository: InMemoryBookPopularityRepository
) -> PopularityRecommendationEngine:
    return PopularityRecommendationEngine(popularity_repository, book_repository)


def test_recommend_ranks_by_loan_count_descending() -> None:
    book_repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    low = _book("978-3-16-148410-0", "Low")
    high = _book("0-306-40615-2", "High")
    book_repository.add(low)
    book_repository.add(high)
    popularity_repository.record(BookPopularity(low.id, 10, "2024-01-01", "2024-01-31"))
    popularity_repository.record(BookPopularity(high.id, 999, "2024-01-01", "2024-01-31"))

    result = _engine(book_repository, popularity_repository).recommend(
        RecommendationQuery(limit=10)
    )

    titles = [item.book.title.value for item in result.recommendation.items]
    assert titles == ["High", "Low"]
    assert result.recommendation.items[0].score == 999.0
    assert result.recommendation.items[0].source == "popularity"


def test_recommend_respects_limit() -> None:
    book_repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]:
        book = _book(isbn)
        book_repository.add(book)
        popularity_repository.record(BookPopularity(book.id, 10, "2024-01-01", "2024-01-31"))

    result = _engine(book_repository, popularity_repository).recommend(
        RecommendationQuery(limit=2)
    )

    assert len(result.recommendation.items) == 2


def test_recommend_returns_empty_when_no_popularity_data() -> None:
    result = _engine(InMemoryBookRepository(), InMemoryBookPopularityRepository()).recommend(
        RecommendationQuery(limit=10)
    )

    assert result.recommendation.items == []


def test_recommend_skips_popularity_with_missing_book() -> None:
    book_repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    orphaned_book_id = BookId.generate()
    popularity_repository.record(
        BookPopularity(orphaned_book_id, 9999, "2024-01-01", "2024-01-31")
    )
    real_book = _book("978-3-16-148410-0", "Real")
    book_repository.add(real_book)
    popularity_repository.record(BookPopularity(real_book.id, 10, "2024-01-01", "2024-01-31"))

    result = _engine(book_repository, popularity_repository).recommend(
        RecommendationQuery(limit=10)
    )

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book.id == real_book.id
