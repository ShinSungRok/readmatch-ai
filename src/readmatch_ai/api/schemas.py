from __future__ import annotations

from pydantic import BaseModel

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.recommendation import RecommendationResult


class BookResponse(BaseModel):
    """API representation of a Book, translated from the Domain entity."""

    id: str
    isbn: str
    title: str
    author: str
    category: str

    @classmethod
    def from_domain(cls, book: Book) -> BookResponse:
        return cls(
            id=str(book.id.value),
            isbn=book.isbn.value,
            title=book.title.value,
            author=book.author.value,
            category=book.category.value,
        )


class RecommendationItemResponse(BaseModel):
    """API representation of a single ranked recommendation."""

    book: BookResponse
    score: float
    source: str


class RecommendationResponse(BaseModel):
    """API representation of a RecommendationResult: an ordered list of recommendations."""

    items: list[RecommendationItemResponse]

    @classmethod
    def from_domain(cls, result: RecommendationResult) -> RecommendationResponse:
        return cls(
            items=[
                RecommendationItemResponse(
                    book=BookResponse.from_domain(item.book),
                    score=item.score,
                    source=item.source,
                )
                for item in result.recommendation.items
            ]
        )
