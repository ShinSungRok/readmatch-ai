from readmatch_ai.application.book_presentation import (
    deterministic_cover_fallback,
    to_book_presentation,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_to_book_presentation_uses_recorded_metadata() -> None:
    book = _book()
    metadata = BookMetadata(
        book.id,
        publisher="Prentice Hall",
        description="A handbook of agile software craftsmanship.",
        cover_url="https://example.test/cover.jpg",
        published_date="2008-08-01",
    )

    presentation = to_book_presentation(book, metadata)

    assert presentation.id == str(book.id.value)
    assert presentation.isbn == book.isbn.value
    assert presentation.title == book.title.value
    assert presentation.author == book.author.value
    assert presentation.category == book.category.value
    assert presentation.publisher == "Prentice Hall"
    assert presentation.description == "A handbook of agile software craftsmanship."
    assert presentation.cover_url == "https://example.test/cover.jpg"
    assert presentation.published_date == "2008-08-01"


def test_to_book_presentation_handles_missing_metadata_safely() -> None:
    book = _book()

    presentation = to_book_presentation(book, None)

    assert presentation.publisher is None
    assert presentation.description is None
    assert presentation.published_date is None
    assert presentation.cover_url == deterministic_cover_fallback(str(book.id.value))


def test_to_book_presentation_falls_back_when_metadata_has_no_cover_url() -> None:
    book = _book()
    metadata = BookMetadata(book.id, publisher="Prentice Hall")

    presentation = to_book_presentation(book, metadata)

    assert presentation.cover_url == deterministic_cover_fallback(str(book.id.value))


def test_deterministic_cover_fallback_is_stable_across_calls() -> None:
    book_id = str(BookId.generate().value)

    assert deterministic_cover_fallback(book_id) == deterministic_cover_fallback(book_id)


def test_deterministic_cover_fallback_varies_by_book_id() -> None:
    fallbacks = {deterministic_cover_fallback(str(BookId.generate().value)) for _ in range(20)}

    # A regression that collapses every book to the same fallback bucket
    # would fail this near-certainly across 20 random ids and 6 buckets.
    assert len(fallbacks) > 1
