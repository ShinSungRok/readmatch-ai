import pytest

from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.application.synchronize_books_use_case import SynchronizeBooksUseCase
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_import_history_repository import (
    InMemoryImportHistoryRepository,
)
from readmatch_ai.infrastructure.in_memory_sync_checkpoint_repository import (
    InMemorySyncCheckpointRepository,
)


class FakeBookDataSource(BookDataSource):
    def __init__(self, books: list[PopularLoanBook]) -> None:
        self._books = books

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        return self._books


class FailingBookDataSource(BookDataSource):
    """Simulates the Data4Library API being unreachable after exhausting retries."""

    def search_popular_loans(self, query: PopularLoanBooksQuery) -> list[PopularLoanBook]:
        raise ConnectionError("simulated Data4Library outage")


def _popular_loan_book(isbn13: str = "978-3-16-148410-0") -> PopularLoanBook:
    return PopularLoanBook(
        isbn13=isbn13,
        title="Clean Code",
        author="Robert C. Martin",
        publisher="Prentice Hall",
        category="Software Engineering",
        loan_count=100,
    )


def _synchronize_use_case(
    data_source: BookDataSource, checkpoint_repository: InMemorySyncCheckpointRepository
) -> SynchronizeBooksUseCase:
    import_use_case = ImportBooksUseCase(
        data_source,
        InMemoryBookRepository(),
        InMemoryBookPopularityRepository(),
        InMemoryImportHistoryRepository(),
    )
    return SynchronizeBooksUseCase(import_use_case, checkpoint_repository)


def test_execute_advances_the_checkpoint_to_the_query_period_end_on_success() -> None:
    checkpoint_repository = InMemorySyncCheckpointRepository()
    use_case = _synchronize_use_case(
        FakeBookDataSource([_popular_loan_book()]), checkpoint_repository
    )

    result = use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert result.checkpoint.period_end == "2024-01-31"
    assert checkpoint_repository.get() == result.checkpoint


def test_execute_uses_the_injected_clock_for_the_checkpoint_timestamp() -> None:
    checkpoint_repository = InMemorySyncCheckpointRepository()
    import_use_case = ImportBooksUseCase(
        FakeBookDataSource([_popular_loan_book()]),
        InMemoryBookRepository(),
        InMemoryBookPopularityRepository(),
        InMemoryImportHistoryRepository(),
    )
    use_case = SynchronizeBooksUseCase(
        import_use_case, checkpoint_repository, clock=lambda: "2024-06-01T00:00:00+00:00"
    )

    result = use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert result.checkpoint.synced_at == "2024-06-01T00:00:00+00:00"


def test_execute_does_not_advance_the_checkpoint_when_the_data_source_fails() -> None:
    checkpoint_repository = InMemorySyncCheckpointRepository()
    use_case = _synchronize_use_case(FailingBookDataSource(), checkpoint_repository)

    with pytest.raises(ConnectionError):
        use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert checkpoint_repository.get() is None


def test_execute_leaves_a_previous_checkpoint_untouched_after_a_later_failure() -> None:
    checkpoint_repository = InMemorySyncCheckpointRepository()
    first_use_case = _synchronize_use_case(
        FakeBookDataSource([_popular_loan_book()]), checkpoint_repository
    )
    first_result = first_use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    failing_use_case = _synchronize_use_case(FailingBookDataSource(), checkpoint_repository)
    with pytest.raises(ConnectionError):
        failing_use_case.execute(PopularLoanBooksQuery("2024-02-01", "2024-02-29"))

    assert checkpoint_repository.get() == first_result.checkpoint


def test_repeated_sync_of_identical_data_reports_unchanged_and_advances_checkpoint() -> None:
    checkpoint_repository = InMemorySyncCheckpointRepository()
    import_use_case = ImportBooksUseCase(
        FakeBookDataSource([_popular_loan_book()]),
        InMemoryBookRepository(),
        InMemoryBookPopularityRepository(),
        InMemoryImportHistoryRepository(),
    )
    use_case = SynchronizeBooksUseCase(import_use_case, checkpoint_repository)
    first_result = use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    second_result = use_case.execute(PopularLoanBooksQuery("2024-02-01", "2024-02-29"))

    assert len(first_result.import_result.imported) == 1
    assert second_result.import_result.imported == []
    assert second_result.import_result.updated == []
    assert len(second_result.import_result.unchanged) == 1
    assert second_result.checkpoint.period_end == "2024-02-29"
