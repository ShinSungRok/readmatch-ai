from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_metadata import BookMetadata

_WHITESPACE_RE = re.compile(r"\s+")


def build_embedding_text(
    book: Book,
    metadata: BookMetadata | None = None,
    keywords: Sequence[str] | None = None,
) -> str:
    """Construct the canonical text a book's embedding is generated from.

    Only semantic fields participate -- title, author, category, and
    (when available) description and keywords. Never id/isbn/publisher/
    cover_url/published_date: provenance and presentation data with no
    bearing on a book's meaning. `metadata`/`keywords` are optional (no
    keyword source exists in this domain yet; the parameter exists so one
    can be added later without changing this function's contract) --
    missing fields are simply omitted, never rendered as a "None" or empty
    placeholder. Every field is whitespace-normalized (internal runs
    collapsed to a single space, leading/trailing trimmed) before joining,
    so formatting differences in source data (extra spaces, newlines) never
    change the resulting text -- and therefore never change the embedding
    -- for otherwise-identical content. Field order is fixed, so the same
    book (+ metadata + keywords) always produces byte-identical text,
    across processes and runs.
    """
    parts = [book.title.value, book.author.value, book.category.value]
    if metadata is not None and metadata.description:
        parts.append(metadata.description)
    if keywords:
        parts.append(" ".join(keywords))
    normalized = [_normalize_whitespace(part) for part in parts]
    return " | ".join(part for part in normalized if part)


def embedding_content_hash(text: str) -> str:
    """A deterministic content hash of the canonical embedding text.

    Used to detect whether a book's embedding-relevant content has changed
    since its embedding was last generated (see the batch embedding
    pipeline) -- comparing this hash is far cheaper than re-encoding, and
    needs no ML model to evaluate.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()
