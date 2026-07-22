from collections.abc import Sequence

from readmatch_ai.application.batch_generate_book_embeddings_use_case import (
    BatchGenerateBookEmbeddingsUseCase,
)
from readmatch_ai.application.refresh_book_embeddings_use_case import (
    RefreshBookEmbeddingsUseCase,
)
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
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


class _RaisingGenerator(BookEmbeddingGenerator):
    """Simulates a real generator failing (e.g. a library/runtime error)."""

    @property
    def model_name(self) -> str:
        return "raising-fake"

    @property
    def model_version(self) -> str:
        return "1"

    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        raise RuntimeError("simulated embedding generator failure")

    def generate_batch(
        self, items: Sequence[tuple[Book, BookMetadata | None]]
    ) -> list[BookEmbedding]:
        raise RuntimeError("simulated embedding generator failure")


def _register(book_repository: InMemoryBookRepository, isbn: str, title: str) -> Book:
    return RegisterBookUseCase(book_repository).execute(
        RegisterBookInput(isbn, title, "An Author", "Fiction")
    )


def test_refresh_generates_for_a_new_book_with_no_stored_embedding() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    generator = DeterministicFakeBookEmbeddingGenerator()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case = RefreshBookEmbeddingsUseCase(batch_use_case)

    result = use_case.execute()

    assert result.requested == 1
    assert result.generated == (str(book.id.value),)
    assert result.skipped == ()
    assert result.failed == ()
    assert embedding_repository.get_by_book_id(book.id) is not None


def test_refresh_skips_a_book_whose_embedding_is_already_current() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    generator = DeterministicFakeBookEmbeddingGenerator()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case = RefreshBookEmbeddingsUseCase(batch_use_case)
    use_case.execute()  # first run: generates and stores

    result = use_case.execute()  # second run (repeated): unchanged content

    assert result.requested == 1
    assert result.generated == ()
    assert result.skipped == (str(book.id.value),)


def test_refresh_regenerates_when_canonical_content_changes() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    generator = DeterministicFakeBookEmbeddingGenerator()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case = RefreshBookEmbeddingsUseCase(batch_use_case)
    use_case.execute()

    metadata_repository.record(BookMetadata(book_id=book.id, description="A new description."))
    result = use_case.execute()

    assert result.generated == (str(book.id.value),)
    assert result.skipped == ()


def test_refresh_regenerates_when_the_configured_model_version_is_stale() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    old_batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository,
        metadata_repository,
        DeterministicFakeBookEmbeddingGenerator(model_version="1"),
        embedding_repository,
    )
    RefreshBookEmbeddingsUseCase(old_batch_use_case).execute()

    new_batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository,
        metadata_repository,
        DeterministicFakeBookEmbeddingGenerator(model_version="2"),
        embedding_repository,
    )
    result = RefreshBookEmbeddingsUseCase(new_batch_use_case).execute()

    assert result.generated == (str(book.id.value),)
    stored = embedding_repository.get_by_book_id(book.id)
    assert stored is not None
    assert stored.model_version == "2"


def test_refresh_returns_empty_result_for_a_catalog_with_no_missing_embeddings() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    generator = DeterministicFakeBookEmbeddingGenerator()
    batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case = RefreshBookEmbeddingsUseCase(batch_use_case)

    result = use_case.execute()

    assert result.requested == 0
    assert result.generated == ()
    assert result.skipped == ()


def test_refresh_reports_failed_instead_of_raising_when_generation_fails() -> None:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    embedding_repository = InMemoryBookEmbeddingRepository()
    _register(book_repository, "978-3-16-148410-0", "A Book")
    batch_use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, _RaisingGenerator(), embedding_repository
    )
    use_case = RefreshBookEmbeddingsUseCase(batch_use_case)

    result = use_case.execute()

    assert result.generated == ()
    assert len(result.failed) == 1
    assert "simulated embedding generator failure" in result.failed[0]
