import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from readmatch_ai.domain.book_data_source import PopularLoanBook, PopularLoanBooksQuery
from readmatch_ai.infrastructure.data4library_book_data_source import (
    Data4LibraryAuthKeyMissingError,
    Data4LibraryBookDataSource,
)

_SAMPLE_RESPONSE = {
    "response": {
        "resultNum": 1,
        "docs": [
            {
                "doc": {
                    "no": "1",
                    "ranking": "1",
                    "bookname": "달러구트 꿈 백화점",
                    "authors": "이미예 지음",
                    "publisher": "팩토리나인",
                    "isbn13": "9791165341909",
                    "loan_count": "12345",
                }
            }
        ],
    }
}


def _mock_urlopen_response(payload: dict[str, Any]) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_missing_auth_key_raises_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATA4LIBRARY_AUTH_KEY", raising=False)

    with pytest.raises(Data4LibraryAuthKeyMissingError):
        Data4LibraryBookDataSource()


def test_auth_key_resolved_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA4LIBRARY_AUTH_KEY", "env-key")

    source = Data4LibraryBookDataSource()

    assert source._auth_key == "env-key"


def test_explicit_auth_key_does_not_require_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATA4LIBRARY_AUTH_KEY", raising=False)

    source = Data4LibraryBookDataSource(auth_key="explicit-key")

    assert source._auth_key == "explicit-key"  # noqa: SLF001


@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_parses_mocked_response(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _mock_urlopen_response(_SAMPLE_RESPONSE)
    source = Data4LibraryBookDataSource(auth_key="test-key")

    books = source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert books == [
        PopularLoanBook(
            isbn13="9791165341909",
            title="달러구트 꿈 백화점",
            author="이미예 지음",
            publisher="팩토리나인",
            loan_count=12345,
        )
    ]
    mock_urlopen.assert_called_once()
    requested_url = mock_urlopen.call_args.args[0]
    assert "authKey=test-key" in requested_url
    assert "startDt=2024-01-01" in requested_url
    assert "endDt=2024-01-31" in requested_url


@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_handles_empty_docs(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _mock_urlopen_response({"response": {"docs": []}})
    source = Data4LibraryBookDataSource(auth_key="test-key")

    books = source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert books == []
