import numpy as np

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.als_model import AlsModel
from readmatch_ai.infrastructure.als_recommendation_engine import ALSRecommendationEngine
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def test_recommend_returns_empty_when_query_has_no_user_id() -> None:
    model = AlsModel(
        user_ids=(UserId.generate(),),
        book_ids=(BookId.generate(),),
        user_factors=np.array([[1.0]]),
        item_factors=np.array([[1.0]]),
    )
    engine = ALSRecommendationEngine(
        model, InMemoryBookRepository(), InMemoryUserBookInteractionRepository()
    )

    result = engine.recommend(RecommendationQuery(limit=10))

    assert result.recommendation.items == []


def test_recommend_returns_empty_for_an_unknown_user() -> None:
    model = AlsModel(
        user_ids=(UserId.generate(),),
        book_ids=(BookId.generate(),),
        user_factors=np.array([[1.0]]),
        item_factors=np.array([[1.0]]),
    )
    engine = ALSRecommendationEngine(
        model, InMemoryBookRepository(), InMemoryUserBookInteractionRepository()
    )

    result = engine.recommend(RecommendationQuery(limit=10, user_id=UserId.generate()))

    assert result.recommendation.items == []


def test_recommend_returns_empty_for_an_empty_model() -> None:
    model = AlsModel(
        user_ids=(), book_ids=(), user_factors=np.zeros((0, 2)), item_factors=np.zeros((0, 2))
    )
    engine = ALSRecommendationEngine(
        model, InMemoryBookRepository(), InMemoryUserBookInteractionRepository()
    )

    result = engine.recommend(RecommendationQuery(limit=10, user_id=UserId.generate()))

    assert result.recommendation.items == []


def test_recommend_ranks_by_score_and_excludes_already_interacted_books() -> None:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    liked = _book("978-3-16-148410-0", "Liked")
    best_new = _book("0-306-40615-2", "BestNew")
    worse_new = _book("9780132350884", "WorseNew")
    for book in (liked, best_new, worse_new):
        book_repository.add(book)
    user_id = UserId.generate()
    interaction_repository.record(
        UserBookInteraction(user_id=user_id, book_id=liked.id, interaction_count=5)
    )

    model = AlsModel(
        user_ids=(user_id,),
        book_ids=(liked.id, best_new.id, worse_new.id),
        user_factors=np.array([[1.0]]),
        # Scores (item_factors @ user_factors): liked=10 (excluded), best_new=3, worse_new=1
        item_factors=np.array([[10.0], [3.0], [1.0]]),
    )
    engine = ALSRecommendationEngine(model, book_repository, interaction_repository)

    result = engine.recommend(RecommendationQuery(limit=10, user_id=user_id))

    titles = [item.book.title.value for item in result.recommendation.items]
    assert titles == ["BestNew", "WorseNew"]
    assert all(item.source == "als" for item in result.recommendation.items)
    assert all(
        item.contributing_sources == frozenset({"als"}) for item in result.recommendation.items
    )


def test_recommend_respects_limit() -> None:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    books = [_book(isbn) for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]]
    for book in books:
        book_repository.add(book)
    user_id = UserId.generate()

    model = AlsModel(
        user_ids=(user_id,),
        book_ids=tuple(book.id for book in books),
        user_factors=np.array([[1.0]]),
        item_factors=np.array([[3.0], [2.0], [1.0]]),
    )
    engine = ALSRecommendationEngine(model, book_repository, interaction_repository)

    result = engine.recommend(RecommendationQuery(limit=2, user_id=user_id))

    assert len(result.recommendation.items) == 2


def test_recommend_skips_a_book_no_longer_in_the_book_repository() -> None:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    known_book = _book("978-3-16-148410-0")
    book_repository.add(known_book)
    missing_book_id = BookId.generate()
    user_id = UserId.generate()

    model = AlsModel(
        user_ids=(user_id,),
        book_ids=(missing_book_id, known_book.id),
        user_factors=np.array([[1.0]]),
        item_factors=np.array([[5.0], [1.0]]),
    )
    engine = ALSRecommendationEngine(model, book_repository, interaction_repository)

    result = engine.recommend(RecommendationQuery(limit=10, user_id=user_id))

    assert len(result.recommendation.items) == 1
    assert result.recommendation.items[0].book.id == known_book.id
