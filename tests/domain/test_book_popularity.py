import pytest

from readmatch_ai.domain.book_popularity import BookPopularityRepository


def test_book_popularity_repository_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookPopularityRepository()  # type: ignore[abstract]
