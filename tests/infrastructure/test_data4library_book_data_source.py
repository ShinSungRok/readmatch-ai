import json
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from readmatch_ai.domain.book_data_source import PopularLoanBook, PopularLoanBooksQuery
from readmatch_ai.infrastructure.data4library_book_data_source import (
    Data4LibraryAuthKeyMissingError,
    Data4LibraryBookDataSource,
    Data4LibraryRequestError,
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
                    "class_nm": "한국소설",
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

    assert source._auth_key == "explicit-key"


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
            category="한국소설",
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


def test_constructor_rejects_a_non_positive_page_size() -> None:
    with pytest.raises(ValueError, match="page_size"):
        Data4LibraryBookDataSource(auth_key="test-key", page_size=0)


def test_constructor_rejects_a_negative_max_retries() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        Data4LibraryBookDataSource(auth_key="test-key", max_retries=-1)


def _doc(isbn13: str, loan_count: str = "1") -> dict[str, Any]:
    return {
        "doc": {
            "bookname": f"Book {isbn13}",
            "authors": "An Author",
            "publisher": "A Publisher",
            "isbn13": isbn13,
            "class_nm": "Fiction",
            "loan_count": loan_count,
        }
    }


@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_requests_page_number_and_size(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _mock_urlopen_response({"response": {"docs": []}})
    source = Data4LibraryBookDataSource(auth_key="test-key", page_size=50)

    source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    requested_url = mock_urlopen.call_args.args[0]
    assert "pageNo=1" in requested_url
    assert "pageSize=50" in requested_url


@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_fetches_a_second_page_when_the_first_is_full(
    mock_urlopen: MagicMock,
) -> None:
    first_page = _mock_urlopen_response(
        {"response": {"docs": [_doc("9781111111111"), _doc("9782222222222")]}}
    )
    second_page = _mock_urlopen_response({"response": {"docs": [_doc("9783333333333")]}})
    mock_urlopen.side_effect = [first_page, second_page]
    source = Data4LibraryBookDataSource(auth_key="test-key", page_size=2)

    books = source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert [book.isbn13 for book in books] == [
        "9781111111111",
        "9782222222222",
        "9783333333333",
    ]
    assert mock_urlopen.call_count == 2
    second_request_url = mock_urlopen.call_args_list[1].args[0]
    assert "pageNo=2" in second_request_url


@patch("time.sleep", return_value=None)
@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_retries_a_transient_error_then_succeeds(
    mock_urlopen: MagicMock, mock_sleep: MagicMock
) -> None:
    success = _mock_urlopen_response({"response": {"docs": [_doc("9781111111111")]}})
    mock_urlopen.side_effect = [URLError("connection refused"), success]
    source = Data4LibraryBookDataSource(auth_key="test-key", max_retries=2)

    books = source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert [book.isbn13 for book in books] == ["9781111111111"]
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once()


@patch("time.sleep", return_value=None)
@patch("readmatch_ai.infrastructure.data4library_book_data_source.urlopen")
def test_search_popular_loans_raises_after_exhausting_retries(
    mock_urlopen: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_urlopen.side_effect = URLError("connection refused")
    source = Data4LibraryBookDataSource(auth_key="test-key", max_retries=2)

    with pytest.raises(Data4LibraryRequestError):
        source.search_popular_loans(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert mock_urlopen.call_count == 3  # 1 initial attempt + 2 retries
    assert mock_sleep.call_count == 2
