from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.domain.explainer import ExplanationReason


@dataclass(frozen=True)
class ExplainedPersonalizedRecommendationItem:
    """A single presentation-ready personalized recommendation plus its explanation.

    Mirrors domain.explainer.ExplainedRecommendationItem's shape exactly,
    except `book` is a presentation-ready BookPresentation (cover_url/
    publisher/description/published_date included) instead of the bare
    Domain Book -- the same enrichment GetHomeFeedUseCase/GetBookDetailUseCase
    already apply via the existing GetBookPresentationUseCase, not a change
    to the Domain explainer or RecommendationItem themselves.
    """

    book: BookPresentation
    score: float
    source: str
    reasons: tuple[ExplanationReason, ...]


@dataclass(frozen=True)
class ExplainedPersonalizedRecommendationResult:
    """An ordered list of ExplainedPersonalizedRecommendationItems (highest-ranked first)."""

    items: list[ExplainedPersonalizedRecommendationItem]
