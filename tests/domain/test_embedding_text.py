from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.embedding_text import build_embedding_text, embedding_content_hash


def _book(
    title: str = "Clean Code", author: str = "Robert C. Martin", category: str = "Software"
) -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title(title),
        author=Author(author),
        category=Category(category),
    )


def test_build_embedding_text_includes_title_author_and_category() -> None:
    book = _book(title="Clean Code", author="Robert C. Martin", category="Software Engineering")

    text = build_embedding_text(book)

    assert "Clean Code" in text
    assert "Robert C. Martin" in text
    assert "Software Engineering" in text


def test_build_embedding_text_omits_description_when_metadata_is_none() -> None:
    book = _book()

    text = build_embedding_text(book, metadata=None)

    assert text == build_embedding_text(book, metadata=BookMetadata(book_id=book.id))


def test_build_embedding_text_includes_description_when_present() -> None:
    book = _book()
    metadata = BookMetadata(book_id=book.id, description="A handbook of agile craftsmanship.")

    text = build_embedding_text(book, metadata)

    assert "A handbook of agile craftsmanship." in text


def test_build_embedding_text_omits_description_when_blank() -> None:
    book = _book()
    metadata = BookMetadata(book_id=book.id, description="   ")

    text = build_embedding_text(book, metadata)

    assert text == build_embedding_text(book)


def test_build_embedding_text_includes_keywords_when_given() -> None:
    book = _book()

    text = build_embedding_text(book, keywords=["agile", "craftsmanship"])

    assert "agile" in text
    assert "craftsmanship" in text


def test_build_embedding_text_never_includes_publisher_or_cover_or_isbn() -> None:
    book = _book()
    metadata = BookMetadata(
        book_id=book.id,
        publisher="Prentice Hall",
        cover_url="https://example.test/cover.jpg",
        published_date="2008-08-01",
    )

    text = build_embedding_text(book, metadata)

    assert "Prentice Hall" not in text
    assert "cover.jpg" not in text
    assert "2008-08-01" not in text
    assert book.isbn.value not in text


def test_build_embedding_text_normalizes_whitespace() -> None:
    messy = _book(title="  Clean   Code\n", author="Robert  C.   Martin")
    tidy = _book(title="Clean Code", author="Robert C. Martin")

    assert build_embedding_text(messy) == build_embedding_text(tidy)


def test_build_embedding_text_is_deterministic() -> None:
    book = _book()
    metadata = BookMetadata(book_id=book.id, description="A classic.")

    first = build_embedding_text(book, metadata)
    second = build_embedding_text(book, metadata)

    assert first == second


def test_build_embedding_text_differs_for_different_content() -> None:
    a = build_embedding_text(_book(title="Clean Code"))
    b = build_embedding_text(_book(title="Refactoring"))

    assert a != b


def test_embedding_content_hash_is_deterministic() -> None:
    text = "Clean Code | Robert C. Martin | Software Engineering"

    assert embedding_content_hash(text) == embedding_content_hash(text)


def test_embedding_content_hash_differs_for_different_text() -> None:
    assert embedding_content_hash("a") != embedding_content_hash("b")


def test_embedding_content_hash_is_a_hex_sha256_digest() -> None:
    digest = embedding_content_hash("some text")

    assert len(digest) == 64
    assert all(char in "0123456789abcdef" for char in digest)
