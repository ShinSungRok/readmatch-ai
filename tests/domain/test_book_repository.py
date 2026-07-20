import pytest

from readmatch_ai.domain.book_repository import BookRepository


def test_book_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookRepository()  # type: ignore[abstract]
