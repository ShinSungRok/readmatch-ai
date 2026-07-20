from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


class FakeBookDataSource(BookDataSource):
    """Mocked BookDataSource returning a fixed, pre-supplied list of books."""

    def __init__(self, books: list[PopularLoanBook]) -> None:
        self._books = books

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        return self._books


def _query() -> PopularLoanBooksQuery:
    return PopularLoanBooksQuery(start_date="2024-01-01", end_date="2024-01-31")


def _popular_loan_book(
    isbn13: str = "978-3-16-148410-0", title: str = "Clean Code"
) -> PopularLoanBook:
    return PopularLoanBook(
        isbn13=isbn13,
        title=title,
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=100,
    )


def test_successful_import_persists_all_books() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="0-306-40615-2", title="Another Book"),
    ]
    use_case = ImportBooksUseCase(FakeBookDataSource(source_books), repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 2
    assert result.skipped_duplicate_isbns == []
    assert repository.get_by_isbn(result.imported[0].isbn) == result.imported[0]
    assert repository.get_by_isbn(result.imported[1].isbn) == result.imported[1]


def test_duplicate_isbn_within_batch_is_skipped_not_fatal() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code (duplicate entry)"),
    ]
    use_case = ImportBooksUseCase(FakeBookDataSource(source_books), repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 1
    assert result.skipped_duplicate_isbns == ["9783161484100"]


def test_duplicate_isbn_against_existing_repository_book_is_skipped() -> None:
    repository = InMemoryBookRepository()
    existing_use_case = ImportBooksUseCase(
        FakeBookDataSource([_popular_loan_book(isbn13="978-3-16-148410-0")]), repository
    )
    existing_use_case.execute(_query())

    reimported_book = _popular_loan_book(isbn13="978-3-16-148410-0", title="Different Title")
    reimport_use_case = ImportBooksUseCase(FakeBookDataSource([reimported_book]), repository)
    result = reimport_use_case.execute(_query())

    assert result.imported == []
    assert result.skipped_duplicate_isbns == ["9783161484100"]


def test_empty_provider_results_returns_empty_result() -> None:
    repository = InMemoryBookRepository()
    use_case = ImportBooksUseCase(FakeBookDataSource([]), repository)

    result = use_case.execute(_query())

    assert result.imported == []
    assert result.skipped_duplicate_isbns == []
