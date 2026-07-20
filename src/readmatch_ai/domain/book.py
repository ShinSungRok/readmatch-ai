from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class BookId:
    value: uuid.UUID

    @classmethod
    def generate(cls) -> BookId:
        return cls(uuid.uuid4())


@dataclass(frozen=True)
class ISBN:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.replace("-", "").replace(" ", "").upper()
        if not _is_valid_isbn(normalized):
            raise ValueError(f"Invalid ISBN: {self.value!r}")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Title:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("Title must not be empty")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Author:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("Author must not be empty")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Category:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("Category must not be empty")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, eq=False)
class Book:
    """A book identified by BookId; equality follows entity identity, not attribute values."""

    id: BookId
    isbn: ISBN
    title: Title
    author: Author
    category: Category

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Book):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


def _is_valid_isbn(candidate: str) -> bool:
    if len(candidate) == 10:
        return _is_valid_isbn10(candidate)
    if len(candidate) == 13:
        return _is_valid_isbn13(candidate)
    return False


def _is_valid_isbn10(candidate: str) -> bool:
    if not candidate[:9].isdigit():
        return False
    if not (candidate[9].isdigit() or candidate[9] == "X"):
        return False
    total = sum(
        (10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(candidate)
    )
    return total % 11 == 0


def _is_valid_isbn13(candidate: str) -> bool:
    if not candidate.isdigit():
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(ch) for i, ch in enumerate(candidate))
    return total % 10 == 0
