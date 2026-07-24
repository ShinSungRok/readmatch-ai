from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)

_API_URL = "http://data4library.kr/api/loanItemSrch"
_AUTH_KEY_ENV_VAR = "DATA4LIBRARY_AUTH_KEY"
_REQUEST_TIMEOUT_SECONDS = 30
_DEFAULT_PAGE_SIZE = 200
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BACKOFF_SECONDS = 1.0


class Data4LibraryAuthKeyMissingError(Exception):
    """Raised when no auth key is provided and DATA4LIBRARY_AUTH_KEY is not set."""


class Data4LibraryRequestError(Exception):
    """Raised when a Data4Library request still fails after exhausting all retries.

    Wraps the last transport-level error (never a raw urllib exception) so
    callers never need to know this adapter uses urllib specifically.
    """


class Data4LibraryBookDataSource(BookDataSource):
    """Adapter for 도서관 정보나루 (Data4Library) Open API.

    Builds the request, calls the endpoint (with retry-with-backoff on
    transient transport errors and automatic pagination), and parses the
    response into PopularLoanBook. Mapping into Book and persistence via
    BookRepository (the import pipeline, application.import_books_use_case)
    is a separate concern.
    """

    def __init__(
        self,
        auth_key: str | None = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_backoff_seconds: float = _DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        if page_size <= 0:
            raise ValueError(f"page_size must be positive, got {page_size!r}")
        if max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {max_retries!r}")
        self._auth_key = auth_key if auth_key is not None else self._read_auth_key_from_env()
        self._page_size = page_size
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    @staticmethod
    def _read_auth_key_from_env() -> str:
        auth_key = os.environ.get(_AUTH_KEY_ENV_VAR)
        if not auth_key:
            raise Data4LibraryAuthKeyMissingError(
                f"Environment variable {_AUTH_KEY_ENV_VAR} is not set"
            )
        return auth_key

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        """Fetch every page of results for `query`, most-loaned first.

        Pages sequentially starting at 1: a page shorter than `page_size`
        is taken as the last page (Data4Library has no separate
        "has more pages" flag), so this makes exactly one request beyond
        necessary only when a result set is an exact multiple of
        `page_size` -- an accepted, minor inefficiency in exchange for not
        needing to parse/trust the API's own `resultNum` total, which is
        not always present in every response shape.
        """
        books: list[PopularLoanBook] = []
        page_no = 1
        while True:
            payload = self._fetch_page(query, page_no)
            docs = payload.get("response", {}).get("docs", [])
            books.extend(self._parse_docs(docs))
            if len(docs) < self._page_size:
                return books
            page_no += 1

    def _fetch_page(self, query: PopularLoanBooksQuery, page_no: int) -> dict[str, Any]:
        url = self._build_request_url(query, page_no)
        last_error: URLError | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(self._retry_backoff_seconds * (2 ** (attempt - 1)))
            try:
                with urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                    payload: dict[str, Any] = json.loads(response.read())
                    return payload
            except URLError as exc:
                last_error = exc
        raise Data4LibraryRequestError(
            f"Data4Library request failed after {self._max_retries + 1} attempt(s)"
        ) from last_error

    def _build_request_url(self, query: PopularLoanBooksQuery, page_no: int) -> str:
        params = {
            "authKey": self._auth_key,
            "startDt": query.start_date,
            "endDt": query.end_date,
            "format": "json",
            "pageNo": page_no,
            "pageSize": self._page_size,
        }
        return f"{_API_URL}?{urlencode(params)}"

    @staticmethod
    def _parse_docs(docs: list[dict[str, Any]]) -> list[PopularLoanBook]:
        return [
            PopularLoanBook(
                isbn13=entry["doc"]["isbn13"],
                title=entry["doc"]["bookname"],
                author=entry["doc"]["authors"],
                publisher=entry["doc"]["publisher"],
                category=entry["doc"]["class_nm"],
                loan_count=int(entry["doc"]["loan_count"]),
                cover_url=entry["doc"].get("bookImageURL") or None,
                published_date=entry["doc"].get("publication_year") or None,
                detail_url=entry["doc"].get("bookDtlUrl") or None,
            )
            for entry in docs
        ]
