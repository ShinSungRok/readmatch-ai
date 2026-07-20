from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)


def _embedding(book_id: BookId, value: float = 0.5) -> BookEmbedding:
    return BookEmbedding(book_id=book_id, vector=(value,), model_name="test-model", dimensions=1)


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
