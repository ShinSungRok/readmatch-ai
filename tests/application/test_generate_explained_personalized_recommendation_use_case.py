from readmatch_ai.application.generate_explained_personalized_recommendation_use_case import (
    FAVORITE_AUTHOR_REASON,
    FAVORITE_CATEGORY_REASON,
    RECENT_SEARCH_MATCH_REASON,
    GenerateExplainedPersonalizedRecommendationUseCase,
)
from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_user_preference_profile_use_case import (
    GetUserPreferenceProfileUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.explainer import (
    ExplanationContext,
    ExplanationReason,
    RecommendationExplainer,
    RecommendationExplanation,
)
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)
from readmatch_ai.infrastructure.in_memory_preference_signal_repository import (
    InMemoryPreferenceSignalRepository,
)


class FakeRecommendationEngine(RecommendationEngine):
    """Mocked RecommendationEngine capturing the query it was called with."""

    def __init__(self, result: RecommendationResult) -> None:
        self._result = result
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return self._result


class FakeRecommendationExplainer(RecommendationExplainer):
    """Mocked RecommendationExplainer capturing the items/context it was called with."""

    def __init__(self, explanations: list[RecommendationExplanation]) -> None:
        self._explanations = explanations
        self.received_items: list[RecommendationItem] | None = None
        self.received_context: ExplanationContext | None = None

    def explain(
        self, items: list[RecommendationItem], context: ExplanationContext
    ) -> list[RecommendationExplanation]:
        self.received_items = items
        self.received_context = context
        return self._explanations


def _book(
    title: str = "Clean Code",
    author: str = "Robert C. Martin",
    category: str = "Software Engineering",
    isbn: str = "978-3-16-148410-0",
) -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN(isbn),
        title=Title(title),
        author=Author(author),
        category=Category(category),
    )


def _item(book: Book) -> RecommendationItem:
    return RecommendationItem(book=book, score=0.8, source="hybrid")


def _book_presentation_use_case() -> GetBookPresentationUseCase:
    """A real GetBookPresentationUseCase -- execute_many() never re-fetches
    from BookRepository (it only needs the Book objects it's already
    given), so an empty repository is fine for every test here.
    """
    return GetBookPresentationUseCase(InMemoryBookRepository(), InMemoryBookMetadataRepository())


def _empty_profile_use_case() -> GetUserPreferenceProfileUseCase:
    """A real GetUserPreferenceProfileUseCase over empty in-memory repositories.

    Always returns an empty (cold-start) profile -- deliberately the real
    class (not a hand-written fake), the same way test_get_personal_library
    _use_case.py wires the real GetBookPresentationUseCase over in-memory
    repositories rather than mocking it.
    """
    return GetUserPreferenceProfileUseCase(
        InMemoryInteractionRepository(),
        InMemoryPreferenceSignalRepository(),
        InMemoryBookRepository(),
    )


def test_execute_builds_the_recommendation_query_from_primitives() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, book_id=book_id, user_id=user_id)


def test_execute_passes_none_book_id_and_user_id_when_omitted() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    use_case.execute(limit=5)

    assert engine.received_query == RecommendationQuery(limit=5, book_id=None, user_id=None)


def test_execute_passes_the_engines_items_and_matching_context_to_the_explainer() -> None:
    item = _item(_book())
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=item.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert explainer.received_items == [item]
    assert explainer.received_context == ExplanationContext(book_id=book_id, user_id=user_id)


def test_execute_pairs_each_item_with_its_reasons_in_order() -> None:
    first, second = _item(_book()), _item(_book())
    engine = FakeRecommendationEngine(
        RecommendationResult(Recommendation(items=[first, second]))
    )
    first_explanation = RecommendationExplanation(
        book_id=first.book.id,
        reasons=(ExplanationReason(type="popularity", message="Popular with many readers."),),
    )
    second_explanation = RecommendationExplanation(book_id=second.book.id, reasons=())
    explainer = FakeRecommendationExplainer([first_explanation, second_explanation])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    result = use_case.execute(limit=5)

    assert [explained.book.id for explained in result.items] == [
        str(first.book.id.value),
        str(second.book.id.value),
    ]
    assert [explained.reasons for explained in result.items] == [
        first_explanation.reasons,
        second_explanation.reasons,
    ]


def test_execute_returns_presentation_ready_books() -> None:
    """Regression guard: this endpoint used to serialize the bare Domain
    Book (no cover_url/publisher/description/published_date), which the
    frontend's BookCard cannot render a cover from.
    """
    item = _item(_book())
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=item.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    result = use_case.execute(limit=5)

    presentation = result.items[0].book
    assert presentation.cover_url is not None and presentation.cover_url != ""
    assert presentation.title == "Clean Code"


def test_execute_returns_empty_result_when_engine_has_no_recommendations() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    result = use_case.execute(limit=10)

    assert result.items == []


def test_execute_does_not_add_profile_reasons_when_user_id_is_omitted() -> None:
    item = _item(_book(category="Software Engineering"))
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    base_explanation = RecommendationExplanation(book_id=item.book.id, reasons=())
    explainer = FakeRecommendationExplainer([base_explanation])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    result = use_case.execute(limit=5)

    assert result.items[0].reasons == base_explanation.reasons


def _profile_use_case_with_positive_book(
    book: Book,
) -> tuple[GetUserPreferenceProfileUseCase, UserId]:
    book_repository = InMemoryBookRepository()
    book_repository.add(book)
    interaction_repository = InMemoryInteractionRepository()
    user_id = UserId.generate()
    interaction_repository.record(UserInteraction(user_id, book.id, InteractionType.LIKE))
    profile_use_case = GetUserPreferenceProfileUseCase(
        interaction_repository, InMemoryPreferenceSignalRepository(), book_repository
    )
    return profile_use_case, user_id


def test_execute_adds_a_favorite_category_reason_when_the_items_category_matches() -> None:
    liked_book = _book(author="Liked Author", category="Software Engineering")
    profile_use_case, user_id = _profile_use_case_with_positive_book(liked_book)
    candidate = _item(_book(author="A Different Author", category="Software Engineering"))
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[candidate])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=candidate.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, profile_use_case, _book_presentation_use_case()
    )

    result = use_case.execute(limit=5, user_id=str(user_id.value))

    reason_types = [reason.type for reason in result.items[0].reasons]
    assert reason_types == [FAVORITE_CATEGORY_REASON]


def test_execute_adds_a_favorite_author_reason_when_the_items_author_matches() -> None:
    liked_book = _book(author="Robert C. Martin")
    profile_use_case, user_id = _profile_use_case_with_positive_book(liked_book)
    candidate = _item(_book(author="Robert C. Martin", category="Different Category"))
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[candidate])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=candidate.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, profile_use_case, _book_presentation_use_case()
    )

    result = use_case.execute(limit=5, user_id=str(user_id.value))

    reason_types = [reason.type for reason in result.items[0].reasons]
    assert reason_types == [FAVORITE_AUTHOR_REASON]


def test_execute_adds_a_recent_search_match_reason_when_a_search_term_matches_the_title() -> None:
    interaction_repository = InMemoryInteractionRepository()
    signal_repository = InMemoryPreferenceSignalRepository()
    user_id = UserId.generate()
    signal_repository.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "healing novel")
    )
    profile_use_case = GetUserPreferenceProfileUseCase(
        interaction_repository, signal_repository, InMemoryBookRepository()
    )
    candidate = _item(_book(title="A Healing Novel About Cats", category="Fiction"))
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[candidate])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=candidate.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, profile_use_case, _book_presentation_use_case()
    )

    result = use_case.execute(limit=5, user_id=str(user_id.value))

    reason_types = [reason.type for reason in result.items[0].reasons]
    assert reason_types == [RECENT_SEARCH_MATCH_REASON]


def test_execute_preserves_existing_reasons_before_appending_profile_reasons() -> None:
    liked_book = _book(author="Liked Author", category="Software Engineering")
    profile_use_case, user_id = _profile_use_case_with_positive_book(liked_book)
    candidate = _item(_book(author="A Different Author", category="Software Engineering"))
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[candidate])))
    popularity_reason = ExplanationReason(type="popularity", message="Popular with many readers.")
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=candidate.book.id, reasons=(popularity_reason,))]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, profile_use_case, _book_presentation_use_case()
    )

    result = use_case.execute(limit=5, user_id=str(user_id.value))

    reason_types = [reason.type for reason in result.items[0].reasons]
    assert reason_types == ["popularity", FAVORITE_CATEGORY_REASON]


def test_execute_adds_no_profile_reasons_for_a_cold_start_user() -> None:
    item = _item(_book())
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    base_explanation = RecommendationExplanation(book_id=item.book.id, reasons=())
    explainer = FakeRecommendationExplainer([base_explanation])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), _book_presentation_use_case()
    )

    result = use_case.execute(limit=5, user_id=str(UserId.generate().value))

    assert result.items[0].reasons == base_explanation.reasons


def test_execute_looks_up_presentation_metadata_in_one_batch_call() -> None:
    """Regression: N+1 guard -- one BookMetadataRepository round-trip for
    the whole result set, never one per item.
    """

    class _CountingMetadataRepository(InMemoryBookMetadataRepository):
        def __init__(self) -> None:
            super().__init__()
            self.batch_call_count = 0

        def get_by_book_ids(self, book_ids: list[BookId]) -> dict[BookId, BookMetadata]:
            self.batch_call_count += 1
            return super().get_by_book_ids(book_ids)

    books = [
        _book(isbn=isbn)
        for isbn in ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]
    ]
    book_repository = InMemoryBookRepository()
    for book in books:
        book_repository.add(book)
    metadata_repository = _CountingMetadataRepository()
    presentation_use_case = GetBookPresentationUseCase(book_repository, metadata_repository)
    items = [_item(book) for book in books]
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=items)))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=item.book.id, reasons=()) for item in items]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(
        engine, explainer, _empty_profile_use_case(), presentation_use_case
    )

    result = use_case.execute(limit=10)

    assert len(result.items) == 3
    assert metadata_repository.batch_call_count == 1
