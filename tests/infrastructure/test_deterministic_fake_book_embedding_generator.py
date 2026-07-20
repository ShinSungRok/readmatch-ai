from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.infrastructure.deterministic_fake_book_embedding_generator import (
    DeterministicFakeBookEmbeddingGenerator,
)


def _book(title: str = "Clean Code", isbn: str = "978-3-16-148410-0") -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_generate_is_deterministic_for_the_same_book_text() -> None:
    book = _book()
    generator = DeterministicFakeBookEmbeddingGenerator()

    first = generator.generate(book)
    second = generator.generate(book)

    assert first.vector == second.vector


def test_generate_differs_for_different_book_text() -> None:
    generator = DeterministicFakeBookEmbeddingGenerator()

    embedding_a = generator.generate(_book(title="Clean Code", isbn="978-3-16-148410-0"))
    embedding_b = generator.generate(_book(title="Refactoring", isbn="0-306-40615-2"))

    assert embedding_a.vector != embedding_b.vector


def test_generate_produces_vector_matching_configured_dimensions() -> None:
    generator = DeterministicFakeBookEmbeddingGenerator(dimensions=16)

    embedding = generator.generate(_book())

    assert embedding.dimensions == 16
    assert len(embedding.vector) == 16
    assert all(0.0 <= component <= 1.0 for component in embedding.vector)


def test_generate_sets_book_id_and_model_name() -> None:
    book = _book()
    generator = DeterministicFakeBookEmbeddingGenerator(model_name="custom-model")

    embedding = generator.generate(book)

    assert embedding.book_id == book.id
    assert embedding.model_name == "custom-model"
