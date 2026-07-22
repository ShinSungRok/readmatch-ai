import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_embedding import BookEmbedding


def test_book_embedding_constructs_with_matching_dimensions() -> None:
    embedding = BookEmbedding(
        book_id=BookId.generate(),
        vector=(0.1, 0.2, 0.3),
        model_name="test-model",
        model_version="1",
        dimensions=3,
        content_hash="abc123",
    )

    assert embedding.dimensions == 3
    assert embedding.vector == (0.1, 0.2, 0.3)


def test_book_embedding_rejects_mismatched_vector_length() -> None:
    with pytest.raises(ValueError, match="vector length"):
        BookEmbedding(
            book_id=BookId.generate(),
            vector=(0.1, 0.2),
            model_name="m",
            model_version="1",
            dimensions=3,
            content_hash="abc123",
        )


def test_book_embedding_rejects_empty_model_name() -> None:
    with pytest.raises(ValueError, match="model_name"):
        BookEmbedding(
            book_id=BookId.generate(),
            vector=(0.1,),
            model_name="   ",
            model_version="1",
            dimensions=1,
            content_hash="abc123",
        )


def test_book_embedding_rejects_empty_model_version() -> None:
    with pytest.raises(ValueError, match="model_version"):
        BookEmbedding(
            book_id=BookId.generate(),
            vector=(0.1,),
            model_name="m",
            model_version="  ",
            dimensions=1,
            content_hash="abc123",
        )


def test_book_embedding_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        BookEmbedding(
            book_id=BookId.generate(),
            vector=(),
            model_name="m",
            model_version="1",
            dimensions=0,
            content_hash="abc123",
        )


def test_book_embedding_rejects_empty_content_hash() -> None:
    with pytest.raises(ValueError, match="content_hash"):
        BookEmbedding(
            book_id=BookId.generate(),
            vector=(0.1,),
            model_name="m",
            model_version="1",
            dimensions=1,
            content_hash="   ",
        )
