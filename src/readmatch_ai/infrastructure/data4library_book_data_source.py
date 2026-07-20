from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)

_API_URL = "http://data4library.kr/api/loanItemSrch"
_AUTH_KEY_ENV_VAR = "DATA4LIBRARY_AUTH_KEY"
_REQUEST_TIMEOUT_SECONDS = 10


class Data4LibraryAuthKeyMissingError(Exception):
    """Raised when no auth key is provided and DATA4LIBRARY_AUTH_KEY is not set."""


class Data4LibraryBookDataSource(BookDataSource):
    """Adapter for 도서관 정보나루 (Data4Library) Open API.

    Networking skeleton only: builds the request, calls the endpoint, and
    parses the response into PopularLoanBook. Mapping into Book and
    persistence via BookRepository (the import pipeline) is out of scope.
    """

    def __init__(self, auth_key: str | None = None) -> None:
        self._auth_key = auth_key if auth_key is not None else self._read_auth_key_from_env()

    @staticmethod
    def _read_auth_key_from_env() -> str:
        auth_key = os.environ.get(_AUTH_KEY_ENV_VAR)
        if not auth_key:
            raise Data4LibraryAuthKeyMissingError(
                f"Environment variable {_AUTH_KEY_ENV_VAR} is not set"
            )
        return auth_key

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        url = self._build_request_url(query)
        with urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
        return self._parse_response(payload)

    def _build_request_url(self, query: PopularLoanBooksQuery) -> str:
        params = {
            "authKey": self._auth_key,
            "startDt": query.start_date,
            "endDt": query.end_date,
            "format": "json",
        }
        return f"{_API_URL}?{urlencode(params)}"

    @staticmethod
    def _parse_response(payload: dict[str, Any]) -> list[PopularLoanBook]:
        docs = payload.get("response", {}).get("docs", [])
        return [
            PopularLoanBook(
                isbn13=entry["doc"]["isbn13"],
                title=entry["doc"]["bookname"],
                author=entry["doc"]["authors"],
                publisher=entry["doc"]["publisher"],
                loan_count=int(entry["doc"]["loan_count"]),
            )
            for entry in docs
        ]
