import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.semantic_recommendation_engine import (
    SemanticRecommendationEngine,
)


def _book(isbn: str, title: str = "Title") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Author"),
        category=Category("Category"),
    )


def _embedding(book_id: BookId, vector: tuple[float, ...]) -> BookEmbedding:
    return BookEmbedding(
        book_id=book_id, vector=vector, model_name="test-model", dimensions=len(vector)
    )


def _engine(
    book_repository: InMemoryBookRepository, embedding_repository: InMemoryBookEmbeddingRepository
) -> SemanticRecommendationEngine:
    return SemanticRecommendationEngine(embedding_repository, book_repository)


def test_recommend_ranks_by_similarity_and_excludes_source_book() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    source = _book("978-3-16-148410-0", "Source")
    close = _book("0-306-40615-2", "Close")
    far = _book("9780132350884", "Far")
    for book in (source, close, far):
        book_repository.add(book)
    embedding_repository.save(_embedding(source.id, (1.0, 0.0)))
    embedding_repository.save(_embedding(close.id, (0.9, 0.1)))
    embedding_repository.save(_embedding(far.id, (0.0, 1.0)))

    result = _engine(book_repository, embedding_repository).recommend(
        RecommendationQuery(limit=10, book_id=source.id)
    )

    titles = [item.book.title.value for item in result.recommendation.items]
    assert titles == ["Close", "Far"]
    assert all(item.source == "semantic" for item in result.recommendation.items)
    assert all(
        item.contributing_sources == frozenset({"semantic"})
        for item in result.recommendation.items
    )
    assert result.recommendation.items[0].score > result.recommendation.items[1].score


def test_recommend_respects_limit() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    source = _book("978-3-16-148410-0", "Source")
    book_repository.add(source)
    embedding_repository.save(_embedding(source.id, (1.0, 0.0)))
    for isbn, vector in [
        ("0-306-40615-2", (0.9, 0.1)),
        ("9780132350884", (0.8, 0.2)),
        ("9780134685991", (0.7, 0.3)),
    ]:
        book = _book(isbn)
        book_repository.add(book)
        embedding_repository.save(_embedding(book.id, vector))

    result = _engine(book_repository, embedding_repository).recommend(
        RecommendationQuery(limit=2, book_id=source.id)
    )

    assert len(result.recommendation.items) == 2


def test_recommend_returns_empty_when_source_book_has_no_embedding() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    source = _book("978-3-16-148410-0", "Source")
    book_repository.add(source)

    result = _engine(book_repository, embedding_repository).recommend(
        RecommendationQuery(limit=10, book_id=source.id)
    )

    assert result.recommendation.items == []


def test_recommend_skips_embedding_with_missing_book() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    source = _book("978-3-16-148410-0", "Source")
    book_repository.add(source)
    embedding_repository.save(_embedding(source.id, (1.0, 0.0)))
    orphaned_book_id = BookId.generate()
    embedding_repository.save(_embedding(orphaned_book_id, (0.9, 0.1)))

    result = _engine(book_repository, embedding_repository).recommend(
        RecommendationQuery(limit=10, book_id=source.id)
    )

    assert result.recommendation.items == []


def test_recommend_raises_when_query_has_no_book_id() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()

    with pytest.raises(ValueError, match="book_id"):
        _engine(book_repository, embedding_repository).recommend(RecommendationQuery(limit=10))
