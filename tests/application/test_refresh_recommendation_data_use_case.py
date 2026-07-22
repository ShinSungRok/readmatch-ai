import pytest

from readmatch_ai.application.batch_generate_book_embeddings_use_case import (
    BatchGenerateBookEmbeddingsUseCase,
)
from readmatch_ai.application.import_books_use_case import ImportBooksUseCase
from readmatch_ai.application.refresh_book_embeddings_use_case import (
    RefreshBookEmbeddingsUseCase,
)
from readmatch_ai.application.refresh_recommendation_data_use_case import (
    RefreshRecommendationDataUseCase,
)
from readmatch_ai.application.synchronize_books_use_case import SynchronizeBooksUseCase
from readmatch_ai.domain.book_data_source import (
    BookDataSource,
    PopularLoanBook,
    PopularLoanBooksQuery,
)
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
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


class _Fixture:
    def __init__(self, data_source: BookDataSource) -> None:
        self.book_repository = InMemoryBookRepository()
        self.popularity_repository = InMemoryBookPopularityRepository()
        self.checkpoint_repository = InMemorySyncCheckpointRepository()
        self.embedding_repository = InMemoryBookEmbeddingRepository()
        metadata_repository = InMemoryBookMetadataRepository()
        generator = DeterministicFakeBookEmbeddingGenerator()

        import_use_case = ImportBooksUseCase(
            data_source,
            self.book_repository,
            self.popularity_repository,
            InMemoryImportHistoryRepository(),
        )
        synchronize_use_case = SynchronizeBooksUseCase(import_use_case, self.checkpoint_repository)
        batch_use_case = BatchGenerateBookEmbeddingsUseCase(
            self.book_repository, metadata_repository, generator, self.embedding_repository
        )
        refresh_embeddings_use_case = RefreshBookEmbeddingsUseCase(batch_use_case)
        self.use_case = RefreshRecommendationDataUseCase(
            synchronize_use_case, refresh_embeddings_use_case
        )


def test_execute_runs_all_stages_for_a_new_book() -> None:
    fixture = _Fixture(FakeBookDataSource([_popular_loan_book()]))

    result = fixture.use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert len(result.synchronization.import_result.imported) == 1
    book_id = result.synchronization.import_result.imported[0].id
    assert result.embedding_refresh.generated == (str(book_id.value),)
    assert result.popularity_refreshed_book_ids == (str(book_id.value),)
    assert fixture.embedding_repository.get_by_book_id(book_id) is not None
    assert fixture.popularity_repository.get_by_book_id(book_id) is not None
    assert fixture.checkpoint_repository.get() == result.synchronization.checkpoint


def test_repeated_execute_is_idempotent() -> None:
    fixture = _Fixture(FakeBookDataSource([_popular_loan_book()]))
    first = fixture.use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    second = fixture.use_case.execute(PopularLoanBooksQuery("2024-02-01", "2024-02-29"))

    assert len(first.synchronization.import_result.imported) == 1
    second_sync = second.synchronization.import_result
    assert second_sync.imported == []
    assert second_sync.updated == []
    assert len(second_sync.unchanged) == 1
    assert second.embedding_refresh.generated == ()
    assert second.embedding_refresh.skipped == (
        str(first.synchronization.import_result.imported[0].id.value),
    )
    assert len(fixture.book_repository.list_all()) == 1
    assert second.synchronization.checkpoint.period_end == "2024-02-29"


def test_execute_does_not_advance_checkpoint_or_run_embedding_refresh_on_sync_failure() -> None:
    fixture = _Fixture(FailingBookDataSource())

    with pytest.raises(ConnectionError):
        fixture.use_case.execute(PopularLoanBooksQuery("2024-01-01", "2024-01-31"))

    assert fixture.checkpoint_repository.get() is None
    assert fixture.book_repository.list_all() == []
