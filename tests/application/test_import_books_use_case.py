from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.domain.book_repository import DuplicateISBNError
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_import_history_repository import (
    InMemoryImportHistoryRepository,
)


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


def _use_case(
    source_books: list[PopularLoanBook],
    repository: InMemoryBookRepository | None = None,
    popularity_repository: InMemoryBookPopularityRepository | None = None,
    history_repository: InMemoryImportHistoryRepository | None = None,
) -> ImportBooksUseCase:
    return ImportBooksUseCase(
        FakeBookDataSource(source_books),
        repository if repository is not None else InMemoryBookRepository(),
        popularity_repository if popularity_repository is not None
        else InMemoryBookPopularityRepository(),
        history_repository if history_repository is not None
        else InMemoryImportHistoryRepository(),
    )


def test_successful_import_persists_all_books() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="0-306-40615-2", title="Another Book"),
    ]
    use_case = _use_case(source_books, repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 2
    assert result.updated == []
    assert result.invalid_records == []
    assert repository.get_by_isbn(result.imported[0].isbn) == result.imported[0]
    assert repository.get_by_isbn(result.imported[1].isbn) == result.imported[1]


def test_duplicate_isbn_within_batch_is_upserted_not_duplicated() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code (revised)"),
    ]
    use_case = _use_case(source_books, repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 1
    assert len(result.updated) == 1
    assert result.imported[0].id == result.updated[0].id
    stored = repository.get_by_isbn(result.imported[0].isbn)
    assert stored is not None
    assert stored.title.value == "Clean Code (revised)"


def test_duplicate_isbn_against_existing_repository_book_is_updated() -> None:
    repository = InMemoryBookRepository()
    first_import = _use_case([_popular_loan_book(isbn13="978-3-16-148410-0")], repository)
    first_result = first_import.execute(_query())
    existing_book_id = first_result.imported[0].id

    reimported_book = _popular_loan_book(isbn13="978-3-16-148410-0", title="Different Title")
    reimport_use_case = _use_case([reimported_book], repository)
    result = reimport_use_case.execute(_query())

    assert result.imported == []
    assert len(result.updated) == 1
    assert result.updated[0].id == existing_book_id
    assert result.updated[0].title.value == "Different Title"
    stored = repository.get_by_isbn(result.updated[0].isbn)
    assert stored is not None
    assert stored.id == existing_book_id
    assert stored.title.value == "Different Title"


def test_reimporting_identical_content_is_classified_unchanged_not_updated() -> None:
    repository = InMemoryBookRepository()
    first_import = _use_case([_popular_loan_book(isbn13="978-3-16-148410-0")], repository)
    first_result = first_import.execute(_query())
    existing_book_id = first_result.imported[0].id

    reimported_book = _popular_loan_book(isbn13="978-3-16-148410-0")
    reimport_use_case = _use_case([reimported_book], repository)
    result = reimport_use_case.execute(_query())

    assert result.imported == []
    assert result.updated == []
    assert len(result.unchanged) == 1
    assert result.unchanged[0].id == existing_book_id


def test_repeated_sync_of_identical_data_creates_no_duplicates_or_false_updates() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="0-306-40615-2", title="Another Book"),
    ]
    use_case = _use_case(source_books, repository)
    first_result = use_case.execute(_query())

    second_result = use_case.execute(_query())

    assert len(first_result.imported) == 2
    assert second_result.imported == []
    assert second_result.updated == []
    assert len(second_result.unchanged) == 2
    assert len(repository.list_all()) == 2


class _RaisingOnceBookRepository(InMemoryBookRepository):
    """Wraps InMemoryBookRepository, raising DuplicateISBNError on the first
    add() call for a chosen ISBN -- simulates a repository-level failure
    (e.g. a race against a concurrent writer) independent of this use
    case's own validation/reconciliation logic."""

    def __init__(self, fail_isbn: str) -> None:
        super().__init__()
        self._fail_isbn = fail_isbn
        self._has_failed = False

    def add(self, book: Book) -> None:
        if not self._has_failed and book.isbn.value == self._fail_isbn:
            self._has_failed = True
            raise DuplicateISBNError(f"simulated race for {self._fail_isbn}")
        super().add(book)


def test_repository_failure_is_recorded_as_failed_not_fatal() -> None:
    repository = _RaisingOnceBookRepository(fail_isbn="9783161484100")
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        _popular_loan_book(isbn13="0-306-40615-2", title="Another Book"),
    ]
    use_case = _use_case(source_books, repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 1
    assert result.imported[0].title.value == "Another Book"
    assert len(result.failed_records) == 1
    assert "9783161484100" in result.failed_records[0]


def test_invalid_record_is_skipped_not_fatal() -> None:
    repository = InMemoryBookRepository()
    source_books = [
        PopularLoanBook(
            isbn13="not-a-valid-isbn",
            title="Broken Record",
            author="Someone",
            publisher="Someone Press",
            category="Fiction",
            loan_count=1,
        ),
        _popular_loan_book(isbn13="0-306-40615-2", title="Valid Book"),
    ]
    use_case = _use_case(source_books, repository)

    result = use_case.execute(_query())

    assert len(result.imported) == 1
    assert result.imported[0].title.value == "Valid Book"
    assert len(result.invalid_records) == 1
    assert "not-a-valid-isbn" in result.invalid_records[0]


def test_empty_provider_results_returns_empty_result() -> None:
    use_case = _use_case([])

    result = use_case.execute(_query())

    assert result.imported == []
    assert result.updated == []
    assert result.invalid_records == []


def test_successful_import_records_popularity_with_provenance() -> None:
    repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    source_book_high_count = PopularLoanBook(
        isbn13="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=777,
    )
    use_case = _use_case([source_book_high_count], repository, popularity_repository)

    result = use_case.execute(_query())

    top = popularity_repository.top_by_loan_count(1)
    assert len(top) == 1
    assert top[0].book_id == result.imported[0].id
    assert top[0].loan_count == 777
    assert top[0].period_start == "2024-01-01"
    assert top[0].period_end == "2024-01-31"


def test_duplicate_isbn_within_batch_still_records_popularity_once() -> None:
    """A duplicate ISBN within one batch (identical content, so classified
    as unchanged the second time) still refreshes the same book_id's
    popularity, rather than creating a second, separate record."""
    repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0"),
        _popular_loan_book(isbn13="978-3-16-148410-0"),
    ]
    use_case = _use_case(source_books, repository, popularity_repository)

    result = use_case.execute(_query())

    top = popularity_repository.top_by_loan_count(10)
    assert len(top) == 1
    assert top[0].book_id == result.unchanged[0].id


def test_reimporting_existing_book_refreshes_popularity_without_duplicate_book() -> None:
    repository = InMemoryBookRepository()
    popularity_repository = InMemoryBookPopularityRepository()
    first_import = _use_case(
        [_popular_loan_book(isbn13="978-3-16-148410-0")], repository, popularity_repository
    )
    first_result = first_import.execute(_query())
    existing_book_id = first_result.imported[0].id

    reimported_book = PopularLoanBook(
        isbn13="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=500,
    )
    second_import = _use_case([reimported_book], repository, popularity_repository)
    second_result = second_import.execute(
        PopularLoanBooksQuery(start_date="2024-02-01", end_date="2024-02-29")
    )

    assert second_result.imported == []
    assert second_result.updated == []
    assert len(second_result.unchanged) == 1
    assert second_result.unchanged[0].id == existing_book_id

    top = popularity_repository.top_by_loan_count(10)
    assert len(top) == 1
    assert top[0].book_id == existing_book_id
    assert top[0].loan_count == 500
    assert top[0].period_start == "2024-02-01"
    assert top[0].period_end == "2024-02-29"


def test_import_history_is_recorded_with_injected_clock() -> None:
    history_repository = InMemoryImportHistoryRepository()
    source_books = [
        _popular_loan_book(isbn13="978-3-16-148410-0", title="Clean Code"),
        PopularLoanBook(
            isbn13="not-a-valid-isbn",
            title="Broken Record",
            author="Someone",
            publisher="Someone Press",
            category="Fiction",
            loan_count=1,
        ),
    ]
    use_case = ImportBooksUseCase(
        FakeBookDataSource(source_books),
        InMemoryBookRepository(),
        InMemoryBookPopularityRepository(),
        history_repository,
        clock=lambda: "2024-06-01T00:00:00+00:00",
    )

    use_case.execute(_query())

    entries = history_repository.list_all()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.imported_at == "2024-06-01T00:00:00+00:00"
    assert entry.period_start == "2024-01-01"
    assert entry.period_end == "2024-01-31"
    assert entry.imported_count == 1
    assert entry.updated_count == 0
    assert entry.unchanged_count == 0
    assert entry.invalid_count == 1
    assert entry.failed_count == 0


def test_import_history_records_one_entry_per_execute_call() -> None:
    history_repository = InMemoryImportHistoryRepository()
    use_case = _use_case(
        [_popular_loan_book(isbn13="978-3-16-148410-0")],
        history_repository=history_repository,
    )

    use_case.execute(_query())
    use_case.execute(PopularLoanBooksQuery(start_date="2024-02-01", end_date="2024-02-29"))

    assert len(history_repository.list_all()) == 2
