import pytest

from readmatch_ai.domain.book_data_source import BookDataSource


def test_book_data_source_is_abstract() -> None:
    with pytest.raises(TypeError):
        BookDataSource()  # type: ignore[abstract]
