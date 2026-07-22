import uuid

from readmatch_ai.application.generate_book_embedding_use_case import (
    GenerateBookEmbeddingUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)
from readmatch_ai.infrastructure.in_memory_book_embedding_repository import (
    InMemoryBookEmbeddingRepository,
)
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
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
    book_repository: InMemoryBookRepository,
    embedding_repository: InMemoryBookEmbeddingRepository,
    metadata_repository: InMemoryBookMetadataRepository | None = None,
) -> GenerateBookEmbeddingUseCase:
    return GenerateBookEmbeddingUseCase(
        book_repository,
        DeterministicFakeBookEmbeddingGenerator(),
        embedding_repository,
        metadata_repository or InMemoryBookMetadataRepository(),
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


def test_execute_produces_a_different_embedding_when_metadata_description_is_recorded() -> None:
    """Sprint 48: the embedding text (and therefore the generated vector)
    changes when a description is recorded, since GenerateBookEmbeddingUseCase
    now passes BookMetadata through to the generator.
    """
    book_repository = InMemoryBookRepository()
    book = _book()
    book_repository.add(book)

    without_metadata = _use_case(book_repository, InMemoryBookEmbeddingRepository()).execute(
        str(book.id.value)
    )

    metadata_repository = InMemoryBookMetadataRepository()
    metadata_repository.record(
        BookMetadata(book_id=book.id, description="A handbook of agile software craftsmanship.")
    )
    with_metadata = _use_case(
        book_repository, InMemoryBookEmbeddingRepository(), metadata_repository
    ).execute(str(book.id.value))

    assert without_metadata is not None
    assert with_metadata is not None
    assert with_metadata.vector != without_metadata.vector
    assert with_metadata.content_hash != without_metadata.content_hash
