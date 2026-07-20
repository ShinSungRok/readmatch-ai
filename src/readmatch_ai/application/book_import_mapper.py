from __future__ import annotations

from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_data_source import PopularLoanBook


def map_to_book(source: PopularLoanBook) -> Book:
    """Map a PopularLoanBook (external DTO) to a Book entity.

    Delegates all validation to the existing domain value objects; raises
    ValueError if the external data violates a domain invariant (e.g. an
    invalid ISBN).
    """
    return Book(
        id=BookId.generate(),
        isbn=ISBN(source.isbn13),
        title=Title(source.title),
        author=Author(source.author),
        category=Category(source.category),
    )
