import pytest

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title


def _make_book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def test_book_id_generate_is_unique() -> None:
    assert BookId.generate() != BookId.generate()


@pytest.mark.parametrize("raw", ["978-3-16-148410-0", "0-306-40615-2", "0306406152"])
def test_isbn_accepts_valid_values(raw: str) -> None:
    isbn = ISBN(raw)
    assert isbn.value == raw.replace("-", "").replace(" ", "").upper()


@pytest.mark.parametrize("raw", ["not-an-isbn", "1234567890123", "030640615X"])
def test_isbn_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError):
        ISBN(raw)


def test_title_strips_whitespace() -> None:
    assert Title("  Clean Code  ").value == "Clean Code"


def test_title_rejects_empty() -> None:
    with pytest.raises(ValueError):
        Title("   ")


def test_author_rejects_empty() -> None:
    with pytest.raises(ValueError):
        Author("")


def test_category_rejects_empty() -> None:
    with pytest.raises(ValueError):
        Category("")


def test_book_equality_is_identity_based() -> None:
    book_id = BookId.generate()
    other_id = BookId.generate()
    isbn = ISBN("978-3-16-148410-0")

    author = Author("X")
    category = Category("Y")

    book_a = Book(id=book_id, isbn=isbn, title=Title("A"), author=author, category=category)
    book_b = Book(
        id=book_id, isbn=isbn, title=Title("Different"), author=author, category=category
    )
    book_c = Book(id=other_id, isbn=isbn, title=Title("A"), author=author, category=category)

    assert book_a == book_b
    assert book_a != book_c
    assert hash(book_a) == hash(book_b)
