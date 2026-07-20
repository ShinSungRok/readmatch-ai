import uuid

from readmatch_ai.application.generate_book_embedding_use_case import (
    GenerateBookEmbeddingUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def _use_case(
    book_repository: InMemoryBookRepository, embedding_repository: InMemoryBookEmbeddingRepository
) -> GenerateBookEmbeddingUseCase:
    return GenerateBookEmbeddingUseCase(
        book_repository, DeterministicFakeBookEmbeddingGenerator(), embedding_repository
    )


def test_execute_generates_and_persists_embedding() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    book = _book()
    book_repository.add(book)

    embedding = _use_case(book_repository, embedding_repository).execute(str(book.id.value))

    assert embedding is not None
    assert embedding.book_id == book.id
    assert embedding_repository.get_by_book_id(book.id) == embedding


def test_execute_replaces_existing_embedding() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    book = _book()
    book_repository.add(book)
    use_case = _use_case(book_repository, embedding_repository)
    first = use_case.execute(str(book.id.value))

    second = use_case.execute(str(book.id.value))

    assert first is not None
    assert second is not None
    stored = embedding_repository.get_by_book_id(book.id)
    assert stored == second
    # Only one embedding is stored for this book (replaced, not duplicated).
    assert stored is not None
    assert stored.book_id == book.id


def test_execute_returns_none_for_missing_book() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()

    result = _use_case(book_repository, embedding_repository).execute(str(uuid.uuid4()))

    assert result is None


def test_execute_persists_nothing_for_missing_book() -> None:
    book_repository = InMemoryBookRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    missing_book_id = BookId.generate()

    _use_case(book_repository, embedding_repository).execute(str(missing_book_id.value))

    assert embedding_repository.get_by_book_id(missing_book_id) is None
