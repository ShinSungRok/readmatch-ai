from __future__ import annotations

from pydantic import BaseModel

from readmatch_ai.application.book_detail import BookDetail
from readmatch_ai.application.book_presentation import BookPresentation
from readmatch_ai.application.home_feed import HomeFeed, HomeFeedItem, HomeFeedSection
from readmatch_ai.application.personal_library import LibraryItem, LibrarySection, PersonalLibrary
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.explainer import (
    ExplainedRecommendationItem,
    ExplainedRecommendationResult,
    ExplanationReason,
)
from readmatch_ai.domain.health import ComponentCheck, HealthStatus, ReadinessStatus
from readmatch_ai.domain.interaction import UserInteraction
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


class BookPresentationResponse(BaseModel):
    """API representation of a BookPresentation (Sprint 39): UI-ready book data."""

    id: str
    isbn: str
    title: str
    author: str
    category: str
    publisher: str | None
    description: str | None
    cover_url: str
    published_date: str | None

    @classmethod
    def from_domain(cls, presentation: BookPresentation) -> BookPresentationResponse:
        return cls(
            id=presentation.id,
            isbn=presentation.isbn,
            title=presentation.title,
            author=presentation.author,
            category=presentation.category,
            publisher=presentation.publisher,
            description=presentation.description,
            cover_url=presentation.cover_url,
            published_date=presentation.published_date,
        )


class HomeFeedItemResponse(BaseModel):
    """API representation of a single HomeFeedItem: a presentation-ready book plus its signal."""

    book: BookPresentationResponse
    score: float
    source: str

    @classmethod
    def from_domain(cls, item: HomeFeedItem) -> HomeFeedItemResponse:
        return cls(
            book=BookPresentationResponse.from_domain(item.book),
            score=item.score,
            source=item.source,
        )


class HomeFeedSectionResponse(BaseModel):
    """API representation of one identified, titled HomeFeedSection."""

    id: str
    title: str
    items: list[HomeFeedItemResponse]

    @classmethod
    def from_domain(cls, section: HomeFeedSection) -> HomeFeedSectionResponse:
        return cls(
            id=section.id,
            title=section.title,
            items=[HomeFeedItemResponse.from_domain(item) for item in section.items],
        )


class HomeFeedResponse(BaseModel):
    """API representation of the consolidated HomeFeed (Sprint 42).

    `hero`/`sections` are both empty (`hero: null`, `sections: []`) when
    there are no books yet -- a valid, safe response, not an error.
    """

    hero: HomeFeedItemResponse | None
    sections: list[HomeFeedSectionResponse]

    @classmethod
    def from_domain(cls, feed: HomeFeed) -> HomeFeedResponse:
        return cls(
            hero=HomeFeedItemResponse.from_domain(feed.hero) if feed.hero is not None else None,
            sections=[HomeFeedSectionResponse.from_domain(section) for section in feed.sections],
        )


class BookSearchResponse(BaseModel):
    """API representation of GET /books/search: presentation-ready matches.

    `items=[]` for a blank query or a query with no matches -- a valid,
    safe response, never an error.
    """

    items: list[BookPresentationResponse]

    @classmethod
    def from_domain(cls, presentations: list[BookPresentation]) -> BookSearchResponse:
        return cls(items=[BookPresentationResponse.from_domain(p) for p in presentations])


class BookDetailResponse(BaseModel):
    """API representation of a BookDetail (Sprint 43): a book plus its similar books."""

    book: BookPresentationResponse
    similar_books: list[HomeFeedItemResponse]

    @classmethod
    def from_domain(cls, detail: BookDetail) -> BookDetailResponse:
        return cls(
            book=BookPresentationResponse.from_domain(detail.book),
            similar_books=[
                HomeFeedItemResponse.from_domain(item) for item in detail.similar_books
            ],
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


class InteractionRequest(BaseModel):
    """Request body for POST /interactions (Sprint 44)."""

    user_id: str
    book_id: str
    interaction_type: str
    value: int | None = None


class InteractionResponse(BaseModel):
    """API representation of a recorded UserInteraction."""

    user_id: str
    book_id: str
    interaction_type: str
    value: int | None = None

    @classmethod
    def from_domain(cls, interaction: UserInteraction) -> InteractionResponse:
        return cls(
            user_id=str(interaction.user_id.value),
            book_id=str(interaction.book_id.value),
            interaction_type=interaction.interaction_type.value,
            value=interaction.value,
        )


class InteractionListResponse(BaseModel):
    """API representation of GET /interactions/{user_id}: every interaction for that user."""

    items: list[InteractionResponse]

    @classmethod
    def from_domain(cls, interactions: list[UserInteraction]) -> InteractionListResponse:
        return cls(items=[InteractionResponse.from_domain(i) for i in interactions])


class LibraryItemResponse(BaseModel):
    """API representation of one LibraryItem: a presentation-ready book plus the interaction."""

    book: BookPresentationResponse
    interaction_type: str
    value: int | None = None

    @classmethod
    def from_domain(cls, item: LibraryItem) -> LibraryItemResponse:
        return cls(
            book=BookPresentationResponse.from_domain(item.book),
            interaction_type=item.interaction_type.value,
            value=item.value,
        )


class LibrarySectionResponse(BaseModel):
    """API representation of one identified, titled LibrarySection."""

    id: str
    title: str
    items: list[LibraryItemResponse]

    @classmethod
    def from_domain(cls, section: LibrarySection) -> LibrarySectionResponse:
        return cls(
            id=section.id,
            title=section.title,
            items=[LibraryItemResponse.from_domain(item) for item in section.items],
        )


class PersonalLibraryResponse(BaseModel):
    """API representation of GET /library/{user_id} (Sprint 45).

    `sections=[]` for a user with no qualifying interactions -- a valid,
    safe response, not an error.
    """

    sections: list[LibrarySectionResponse]

    @classmethod
    def from_domain(cls, library: PersonalLibrary) -> PersonalLibraryResponse:
        return cls(
            sections=[LibrarySectionResponse.from_domain(section) for section in library.sections]
        )


class ComponentCheckResponse(BaseModel):
    """API representation of one ComponentCheck."""

    name: str
    available: bool
    detail: str | None = None

    @classmethod
    def from_domain(cls, check: ComponentCheck) -> ComponentCheckResponse:
        return cls(name=check.name, available=check.available, detail=check.detail)


class HealthResponse(BaseModel):
    """API representation of a HealthStatus."""

    healthy: bool
    checks: list[ComponentCheckResponse]

    @classmethod
    def from_domain(cls, status: HealthStatus) -> HealthResponse:
        return cls(
            healthy=status.healthy,
            checks=[ComponentCheckResponse.from_domain(check) for check in status.checks],
        )


class ReadinessResponse(BaseModel):
    """API representation of a ReadinessStatus.

    `mode` (Sprint 32) is the active APPLICATION_MODE ("development",
    "test", "production"), or `null` if it could not be resolved -- a
    minimal, safe addition (never a raw configuration value) sourced from
    ApplicationContext.runtime_configuration_summary, not from
    ReadinessStatus itself (which stays transport-independent and
    unchanged; see runtime_configuration.RuntimeConfigurationSummary).
    """

    ready: bool
    checks: list[ComponentCheckResponse]
    mode: str | None = None

    @classmethod
    def from_domain(cls, status: ReadinessStatus, mode: str | None = None) -> ReadinessResponse:
        return cls(
            ready=status.ready,
            checks=[ComponentCheckResponse.from_domain(check) for check in status.checks],
            mode=mode,
        )
