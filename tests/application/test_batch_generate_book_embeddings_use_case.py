from collections.abc import Sequence

from readmatch_ai.application.batch_generate_book_embeddings_use_case import (
    BatchGenerateBookEmbeddingsUseCase,
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


class _CountingGenerator(BookEmbeddingGenerator):
    """Wraps a real generator, counting how many times generate_batch is called."""

    def __init__(self, inner: BookEmbeddingGenerator) -> None:
        self._inner = inner
        self.generate_batch_call_count = 0

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    @property
    def model_version(self) -> str:
        return self._inner.model_version

    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        return self._inner.generate(book, metadata)

    def generate_batch(
        self, items: Sequence[tuple[Book, BookMetadata | None]]
    ) -> list[BookEmbedding]:
        self.generate_batch_call_count += 1
        return self._inner.generate_batch(items)


def _setup() -> tuple[
    InMemoryBookRepository,
    InMemoryBookMetadataRepository,
    InMemoryBookEmbeddingRepository,
    DeterministicFakeBookEmbeddingGenerator,
]:
    return (
        InMemoryBookRepository(),
        InMemoryBookMetadataRepository(),
        InMemoryBookEmbeddingRepository(),
        DeterministicFakeBookEmbeddingGenerator(),
    )


def _register(book_repository: InMemoryBookRepository, isbn: str, title: str) -> Book:
    return RegisterBookUseCase(book_repository).execute(
        RegisterBookInput(isbn, title, "An Author", "Fiction")
    )


def test_execute_generates_embeddings_for_books_with_none_stored() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )

    stats = use_case.execute()

    assert stats.total_books == 1
    assert stats.generated_book_ids == (str(book.id.value),)
    assert stats.skipped_book_ids == ()
    assert embedding_repository.get_by_book_id(book.id) is not None


def test_execute_returns_empty_stats_for_an_empty_catalog() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )

    stats = use_case.execute()

    assert stats.total_books == 0
    assert stats.generated_book_ids == ()
    assert stats.skipped_book_ids == ()


def test_execute_skips_a_book_whose_embedding_is_already_current() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case.execute()  # first run: generates and stores

    stats = use_case.execute()  # second run: nothing changed

    assert stats.generated_book_ids == ()
    assert stats.skipped_book_ids == (str(book.id.value),)


def test_execute_regenerates_when_content_changes() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    use_case.execute()
    before = embedding_repository.get_by_book_id(book.id)

    metadata_repository.record(BookMetadata(book_id=book.id, description="A new description."))
    stats = use_case.execute()

    assert stats.generated_book_ids == (str(book.id.value),)
    after = embedding_repository.get_by_book_id(book.id)
    assert before is not None and after is not None
    assert after.content_hash != before.content_hash
    assert after.vector != before.vector


def test_execute_regenerates_when_model_version_changes() -> None:
    book_repository, metadata_repository, embedding_repository, _generator = _setup()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    old_generator = DeterministicFakeBookEmbeddingGenerator(model_version="1")
    BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, old_generator, embedding_repository
    ).execute()

    new_generator = DeterministicFakeBookEmbeddingGenerator(model_version="2")
    stats = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, new_generator, embedding_repository
    ).execute()

    assert stats.generated_book_ids == (str(book.id.value),)
    stored = embedding_repository.get_by_book_id(book.id)
    assert stored is not None
    assert stored.model_version == "2"


def test_execute_regenerates_when_model_name_changes() -> None:
    book_repository, metadata_repository, embedding_repository, _generator = _setup()
    book = _register(book_repository, "978-3-16-148410-0", "A Book")
    BatchGenerateBookEmbeddingsUseCase(
        book_repository,
        metadata_repository,
        DeterministicFakeBookEmbeddingGenerator(model_name="model-a"),
        embedding_repository,
    ).execute()

    stats = BatchGenerateBookEmbeddingsUseCase(
        book_repository,
        metadata_repository,
        DeterministicFakeBookEmbeddingGenerator(model_name="model-b"),
        embedding_repository,
    ).execute()

    assert stats.generated_book_ids == (str(book.id.value),)


def test_execute_calls_generate_batch_exactly_once_for_multiple_books_needing_it() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    _register(book_repository, "978-3-16-148410-0", "A")
    _register(book_repository, "0-306-40615-2", "B")
    _register(book_repository, "9780132350884", "C")
    counting_generator = _CountingGenerator(generator)
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, counting_generator, embedding_repository
    )

    stats = use_case.execute()

    assert stats.generated_count == 3
    assert counting_generator.generate_batch_call_count == 1


def test_execute_processes_books_in_deterministic_id_order() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    books = [
        _register(book_repository, isbn, f"Book {i}")
        for i, isbn in enumerate(
            ["978-3-16-148410-0", "0-306-40615-2", "9780132350884", "978-0-13-468599-1"]
        )
    ]
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )

    first = use_case.execute()
    expected_order = tuple(sorted(str(book.id.value) for book in books))

    assert first.generated_book_ids == expected_order


def test_execute_stats_generated_and_skipped_counts_match_id_tuples() -> None:
    book_repository, metadata_repository, embedding_repository, generator = _setup()
    already_current = _register(book_repository, "978-3-16-148410-0", "Already Current")
    needs_generation = _register(book_repository, "0-306-40615-2", "Needs Generation")
    use_case = BatchGenerateBookEmbeddingsUseCase(
        book_repository, metadata_repository, generator, embedding_repository
    )
    # Pre-generate only the first book so the second run has one to skip.
    embedding_repository.save(generator.generate(already_current))

    stats = use_case.execute()

    assert stats.total_books == 2
    assert stats.generated_count == 1
    assert stats.skipped_count == 1
    assert stats.generated_book_ids == (str(needs_generation.id.value),)
    assert stats.skipped_book_ids == (str(already_current.id.value),)
