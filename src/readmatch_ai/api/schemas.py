from __future__ import annotations

from pydantic import BaseModel

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.explainer import (
    ExplainedRecommendationItem,
    ExplainedRecommendationResult,
    ExplanationReason,
)
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


class ExplanationReasonResponse(BaseModel):
    """API representation of one deterministic, evidence-based ExplanationReason.

    `type` is a fixed vocabulary (see domain.explainer's *_REASON constants:
    "popularity", "semantic_similarity", "collaborative_behavior", "novelty",
    "diversity") -- not free text. `message` is a human-readable rendering of
    the same reason, not an independent claim.
    """

    type: str
    message: str

    @classmethod
    def from_domain(cls, reason: ExplanationReason) -> ExplanationReasonResponse:
        return cls(type=reason.type, message=reason.message)


class ExplainedRecommendationItemResponse(BaseModel):
    """A ranked recommendation plus zero or more structured explanation reasons.

    An empty `reasons` list is valid and expected when evidence is limited
    (e.g. a popularity-only fallback for a cold-start user) -- never padded
    with a fabricated reason.
    """

    book: BookResponse
    score: float
    source: str
    reasons: list[ExplanationReasonResponse]

    @classmethod
    def from_domain(
        cls, explained_item: ExplainedRecommendationItem
    ) -> ExplainedRecommendationItemResponse:
        return cls(
            book=BookResponse.from_domain(explained_item.item.book),
            score=explained_item.item.score,
            source=explained_item.item.source,
            reasons=[
                ExplanationReasonResponse.from_domain(reason)
                for reason in explained_item.explanation.reasons
            ],
        )


class ExplainedRecommendationResponse(BaseModel):
    """API representation of an ExplainedRecommendationResult."""

    items: list[ExplainedRecommendationItemResponse]

    @classmethod
    def from_domain(
        cls, result: ExplainedRecommendationResult
    ) -> ExplainedRecommendationResponse:
        return cls(
            items=[
                ExplainedRecommendationItemResponse.from_domain(explained_item)
                for explained_item in result.items
            ]
        )
