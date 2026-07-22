from __future__ import annotations

import hashlib
from dataclasses import dataclass

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_metadata import BookMetadata

# Frontend-provided placeholder assets (added in Sprint 40/41), one per
# fallback bucket -- kept in sync with PLACEHOLDER_COVER_COUNT below.
_PLACEHOLDER_COVER_COUNT = 6


@dataclass(frozen=True)
class BookPresentation:
    """UI-ready book information: the Book aggregate plus optional metadata.

    An application-layer DTO, not a Domain concept -- it exists so
    presentation/UI needs (a guaranteed, deterministic cover_url; safely
    absent publisher/description/published_date) never leak into the core
    recommendation Domain (Book, ranking, scoring all stay untouched).
    """

    id: str
    isbn: str
    title: str
    author: str
    category: str
    publisher: str | None
    description: str | None
    cover_url: str
    published_date: str | None


def deterministic_cover_fallback(book_id: str) -> str:
    """A stable placeholder cover URL derived only from the book id.

    Deterministic (same book id always maps to the same fallback, across
    processes and runs) and requires no network call or generated image --
    the frontend supplies the actual placeholder assets at these paths.
    """
    digest = hashlib.sha256(book_id.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % _PLACEHOLDER_COVER_COUNT
    return f"/covers/placeholder-{bucket}.svg"


def to_book_presentation(book: Book, metadata: BookMetadata | None) -> BookPresentation:
    """Merge a Book with its optional BookMetadata into a BookPresentation.

    Missing metadata (or a missing/blank cover_url within it) is handled
    safely: every field other than cover_url stays None, and cover_url
    always falls back to deterministic_cover_fallback -- the presentation
    layer never leaves the UI without a cover to render.
    """
    book_id = str(book.id.value)
    cover_url = (metadata.cover_url if metadata else None) or deterministic_cover_fallback(book_id)
    return BookPresentation(
        id=book_id,
        isbn=book.isbn.value,
        title=book.title.value,
        author=book.author.value,
        category=book.category.value,
        publisher=metadata.publisher if metadata else None,
        description=metadata.description if metadata else None,
        cover_url=cover_url,
        published_date=metadata.published_date if metadata else None,
    )
