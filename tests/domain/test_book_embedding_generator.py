import pytest

from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator


def test_book_embedding_generator_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookEmbeddingGenerator()  # type: ignore[abstract]
