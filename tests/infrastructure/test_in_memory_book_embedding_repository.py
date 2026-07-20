from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)


def _embedding(book_id: BookId, value: float = 0.5) -> BookEmbedding:
    return BookEmbedding(book_id=book_id, vector=(value,), model_name="test-model", dimensions=1)


def _embedding_2d(book_id: BookId, vector: tuple[float, float]) -> BookEmbedding:
    return BookEmbedding(book_id=book_id, vector=vector, model_name="test-model", dimensions=2)


def test_get_by_book_id_missing_returns_none() -> None:
    repository = InMemoryBookEmbeddingRepository()

    assert repository.get_by_book_id(BookId.generate()) is None


def test_save_and_get_by_book_id() -> None:
    repository = InMemoryBookEmbeddingRepository()
    book_id = BookId.generate()
    embedding = _embedding(book_id)

    repository.save(embedding)

    assert repository.get_by_book_id(book_id) == embedding


def test_save_upserts_existing_book_id() -> None:
    repository = InMemoryBookEmbeddingRepository()
    book_id = BookId.generate()
    repository.save(_embedding(book_id, value=0.1))

    repository.save(_embedding(book_id, value=0.9))

    assert repository.get_by_book_id(book_id) == _embedding(book_id, value=0.9)


def test_find_similar_returns_empty_list_when_no_embeddings_stored() -> None:
    repository = InMemoryBookEmbeddingRepository()

    assert repository.find_similar((1.0, 0.0), limit=5) == []


def test_find_similar_ranks_by_cosine_similarity_descending() -> None:
    repository = InMemoryBookEmbeddingRepository()
    closest = _embedding_2d(BookId.generate(), (1.0, 0.0))
    middle = _embedding_2d(BookId.generate(), (0.9, 0.1))
    farthest = _embedding_2d(BookId.generate(), (0.0, 1.0))
    repository.save(farthest)
    repository.save(closest)
    repository.save(middle)

    result = repository.find_similar((1.0, 0.0), limit=3)

    assert result == [closest, middle, farthest]


def test_find_similar_truncates_to_limit() -> None:
    repository = InMemoryBookEmbeddingRepository()
    closest = _embedding_2d(BookId.generate(), (1.0, 0.0))
    farthest = _embedding_2d(BookId.generate(), (0.0, 1.0))
    repository.save(farthest)
    repository.save(closest)

    result = repository.find_similar((1.0, 0.0), limit=1)

    assert result == [closest]


def test_find_similar_skips_embeddings_with_mismatched_dimensions() -> None:
    repository = InMemoryBookEmbeddingRepository()
    matching = _embedding_2d(BookId.generate(), (1.0, 0.0))
    mismatched = _embedding(BookId.generate(), value=1.0)
    repository.save(matching)
    repository.save(mismatched)

    result = repository.find_similar((1.0, 0.0), limit=5)

    assert result == [matching]
