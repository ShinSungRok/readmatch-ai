import pytest

from readmatch_ai.domain.book_embedding_repository import BookEmbeddingRepository


def test_book_embedding_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookEmbeddingRepository()  # type: ignore[abstract]
