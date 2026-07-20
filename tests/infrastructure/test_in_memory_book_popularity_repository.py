from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.infrastructure.in_memory_book_popularity_repository import (
    InMemoryBookPopularityRepository,
)


def _popularity(book_id: BookId, loan_count: int) -> BookPopularity:
    return BookPopularity(
        book_id=book_id, loan_count=loan_count, period_start="2024-01-01", period_end="2024-01-31"
    )


def test_top_by_loan_count_orders_descending() -> None:
    repository = InMemoryBookPopularityRepository()
    low, mid, high = BookId.generate(), BookId.generate(), BookId.generate()
    repository.record(_popularity(low, 5))
    repository.record(_popularity(high, 30))
    repository.record(_popularity(mid, 15))

    top = repository.top_by_loan_count(3)

    assert [p.book_id for p in top] == [high, mid, low]


def test_top_by_loan_count_respects_limit() -> None:
    repository = InMemoryBookPopularityRepository()
    for i in range(5):
        repository.record(_popularity(BookId.generate(), loan_count=i))

    assert len(repository.top_by_loan_count(2)) == 2


def test_top_by_loan_count_empty_returns_empty_list() -> None:
    repository = InMemoryBookPopularityRepository()

    assert repository.top_by_loan_count(10) == []


def test_record_upserts_existing_book_id() -> None:
    repository = InMemoryBookPopularityRepository()
    book_id = BookId.generate()
    repository.record(_popularity(book_id, 10))

    repository.record(BookPopularity(book_id, 999, "2024-02-01", "2024-02-28"))

    top = repository.top_by_loan_count(1)
    assert top == [BookPopularity(book_id, 999, "2024-02-01", "2024-02-28")]
